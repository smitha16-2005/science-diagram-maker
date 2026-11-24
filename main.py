
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from gemini_service import generate_svg, MODEL_NAME
from validator import validate_svg


# --------------------------------------------------
# PATHS AND CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
STATIC_DIR = BASE_DIR / "static"
RESULTS_FILE = DATA_DIR / "results.json"

DATA_DIR.mkdir(exist_ok=True)

CONCEPTS = {
    "pythagoras": {
        "name": "Pythagoras' Theorem",
        "prompt": """
Explain Pythagoras' theorem using an animated right-angled triangle.
Show the sides a, b and hypotenuse c.
Clearly display a² + b² = c².
Explain that the hypotenuse is the longest side.
"""
    },
    "circle": {
        "name": "Parts of a Circle",
        "prompt": """
Create an educational animated diagram of a circle.
Clearly label centre, radius, diameter, chord and circumference.
Show that the diameter passes through the centre
and is twice the radius.
"""
    },
    "series_circuit": {
        "name": "Series Circuit",
        "prompt": """
Create an animated educational diagram of a series circuit.
Show a cell, wires and two bulbs connected in one loop.
Show current flowing through the same path.
Explain that the same current flows everywhere
and cell voltage is shared between components.
"""
    },
    "photosynthesis": {
        "name": "Photosynthesis",
        "prompt": """
Create an animated educational diagram explaining photosynthesis.
Show a plant receiving sunlight, carbon dioxide and water.
Show glucose being produced and oxygen released.
Label chlorophyll, sunlight, CO2, water, glucose and oxygen.
"""
    },
    "states_of_matter": {
        "name": "States of Matter",
        "prompt": """
Create an animated educational diagram comparing solid,
liquid and gas particle arrangements.
Show solid particles closely packed and vibrating in place.
Show liquid particles close together but moving past each other.
Show gas particles far apart and moving quickly.
"""
    }
}


# --------------------------------------------------
# REQUEST MODELS
# --------------------------------------------------

class ReviewRequest(BaseModel):
    decision: str
    note: str = ""


# --------------------------------------------------
# JSON STORAGE
# --------------------------------------------------

def load_results():
    """Load saved results safely using UTF-8 encoding."""

    if not RESULTS_FILE.exists():
        return {}

    try:
        with open(RESULTS_FILE, "r", encoding="utf-8") as file:
            data = json.load(file)

        return data if isinstance(data, dict) else {}

    except (json.JSONDecodeError, OSError) as error:
        print(f"Could not read results.json: {error}")
        return {}


def save_results(results):
    """Save results safely using UTF-8 encoding."""

    with open(RESULTS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            results,
            file,
            indent=4,
            ensure_ascii=False
        )


# --------------------------------------------------
# SVG GENERATION AND VALIDATION
# --------------------------------------------------

def process_concept(concept_id):
    """
    Generate SVG, validate it, and retry once if validation fails.
    Preserve the previous human review when regenerating a concept.
    """

    if concept_id not in CONCEPTS:
        raise ValueError(f"Unknown concept: {concept_id}")

    concept = CONCEPTS[concept_id]

    # Preserve any existing reviewer decision and feedback.
    existing_results = load_results()

    previous_review = existing_results.get(
        concept_id, {}
    ).get(
        "review",
        {
            "decision": "pending",
            "note": ""
        }
    )

    correction = None
    generation_data = None
    validation_result = None
    validation_retries = 0

    for attempt in range(2):

        generation_data = generate_svg(
            concept["prompt"],
            correction=correction
        )

        validation_result = validate_svg(
            generation_data["svg"]
        )

        if validation_result["valid"]:
            break

        if attempt == 0:
            validation_retries += 1

            correction = "\n".join(
                validation_result.get("errors", [])
            )

            print(
                f"Validation failed for {concept['name']}. "
                "Retrying once with corrections..."
            )

    result = {
        "id": concept_id,
        "concept": concept["name"],
        "subject": concept["prompt"],
        "svg": generation_data["svg"],
        "model": generation_data["model"],
        "input_tokens": generation_data["input_tokens"],
        "output_tokens": generation_data["output_tokens"],
        "estimated_cost_usd": generation_data["estimated_cost_usd"],
        "api_retries": generation_data.get("api_retries", 0),
        "validation_retries": validation_retries,
        "total_retries": (
            generation_data.get("api_retries", 0)
            + validation_retries
        ),
        "validation": validation_result,
        "status": (
            "passed"
            if validation_result["valid"]
            else "failed"
        ),
        "generated_at": datetime.now(timezone.utc).isoformat(),

        # Keep the previous review instead of resetting it.
        "review": previous_review
    }

    return result


def generate_all():
    """Generate all five concepts and save results after each one."""

    results = load_results()

    for concept_id, concept in CONCEPTS.items():

        print("\n" + "=" * 55)
        print(f"Generating: {concept['name']}")
        print("=" * 55)

        try:
            result = process_concept(concept_id)
            results[concept_id] = result

            print(f"Status: {result['status']}")
            print(f"Cost: ${result['estimated_cost_usd']}")
            print(f"Retries: {result['total_retries']}")

        except Exception as error:

            print(f"Generation failed: {error}")

            # Preserve the existing review even on generation failure.
            previous_review = results.get(
                concept_id, {}
            ).get(
                "review",
                {
                    "decision": "pending",
                    "note": ""
                }
            )

            results[concept_id] = {
                "id": concept_id,
                "concept": concept["name"],
                "status": "error",
                "error": str(error),
                "model": MODEL_NAME,
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "review": previous_review
            }

        save_results(results)

    print("\nAll generation tasks completed.")
    print(f"Results saved to: {RESULTS_FILE}")


# --------------------------------------------------
# FASTAPI APPLICATION
# --------------------------------------------------

app = FastAPI(
    title="Science Diagram Maker",
    description="AI-powered animated science diagram generator",
    version="1.0.0"
)

app.mount(
    "/static",
    StaticFiles(directory=str(STATIC_DIR)),
    name="static"
)


# --------------------------------------------------
# WEBPAGE
# --------------------------------------------------

@app.get("/", response_class=HTMLResponse)
def home():
    index_file = STATIC_DIR / "index.html"

    if not index_file.exists():
        raise HTTPException(
            status_code=500,
            detail="Dashboard file static/index.html was not found."
        )

    results = load_results()

    initial_data = json.dumps(
        list(results.values()),
        ensure_ascii=False
    )

    initial_data = (
        initial_data
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
    )

    html = index_file.read_text(encoding="utf-8")

    html = html.replace(
        "__INITIAL_RESULTS__",
        initial_data
    )

    return HTMLResponse(content=html)


# --------------------------------------------------
# API: CONCEPTS
# --------------------------------------------------

@app.get("/api/concepts")
def get_concepts():

    return [
        {
            "id": concept_id,
            "name": concept["name"],
            "prompt": concept["prompt"]
        }
        for concept_id, concept in CONCEPTS.items()
    ]


# --------------------------------------------------
# API: SAVED RESULTS
# --------------------------------------------------

@app.get("/api/results")
def get_results():

    results = load_results()

    return {
        "results": list(results.values()),
        "total": len(results)
    }


# --------------------------------------------------
# API: GENERATE ONE CONCEPT
# --------------------------------------------------

@app.post("/api/generate/{concept_id}")
def generate_one(concept_id: str):

    if concept_id not in CONCEPTS:
        raise HTTPException(
            status_code=404,
            detail="Concept not found."
        )

    try:
        result = process_concept(concept_id)

        results = load_results()
        results[concept_id] = result
        save_results(results)

        return result

    except Exception as error:

        raise HTTPException(
            status_code=500,
            detail=f"Generation failed: {str(error)}"
        )


# --------------------------------------------------
# API: APPROVE / REJECT
# --------------------------------------------------

@app.post("/api/review/{concept_id}")
def review_concept(concept_id: str, request: ReviewRequest):

    if concept_id not in CONCEPTS:
        raise HTTPException(
            status_code=404,
            detail="Concept not found."
        )

    decision = request.decision.strip().lower()

    if decision not in ["approved", "rejected"]:
        raise HTTPException(
            status_code=400,
            detail="Decision must be approved or rejected."
        )

    results = load_results()

    if concept_id not in results:
        raise HTTPException(
            status_code=404,
            detail="Generate this concept before reviewing it."
        )

    results[concept_id]["review"] = {
        "decision": decision,
        "note": request.note,
        "reviewed_at": datetime.now(timezone.utc).isoformat()
    }

    save_results(results)

    return {
        "message": f"Concept {decision} successfully.",
        "result": results[concept_id]
    }


# --------------------------------------------------
# API: HEALTH CHECK
# --------------------------------------------------

@app.get("/api/health")
def health_check():

    return {
        "status": "healthy",
        "model": MODEL_NAME,
        "saved_results": len(load_results())
    }


# --------------------------------------------------
# RUN GENERATION FROM COMMAND LINE
# --------------------------------------------------

if __name__ == "__main__":

    if "--generate-all" in sys.argv:
        generate_all()

    else:
        import uvicorn

        uvicorn.run(
            "main:app",
            host="127.0.0.1",
            port=8000,
            reload=True
        )

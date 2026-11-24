
import os
import re
import time

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
MODEL_NAME = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY is missing. Check your .env file.")

client = genai.Client(api_key=API_KEY)

# Reference prices per million tokens (USD).
# These are estimates, not actual billing records.
INPUT_PRICE_PER_MILLION = 0.30
OUTPUT_PRICE_PER_MILLION = 2.50


# --------------------------------------------------
# PROMPT GENERATION
# --------------------------------------------------

def build_prompt(concept, correction=None):

    prompt = f"""
You are an expert GCSE science and mathematics educational illustrator.

Create ONE accurate, visually attractive, animated SVG diagram
for the following concept:

{concept}

STRICT REQUIREMENTS:
1. Return ONLY valid SVG code. No Markdown or explanations.
2. Use an SVG viewBox of "0 0 800 500".
3. Include a descriptive <title>.
4. Include at least 3 readable text labels.
5. Include at least one CSS or SVG SMIL animation.
6. Keep every visual element inside the viewBox.
7. Use clear arrows, shapes and colours where appropriate.
8. Make the diagram scientifically accurate.
9. Use GCSE-level terminology.
10. Make all labels readable and avoid overlapping text.
11. Use self-contained SVG. No external images or libraries.
12. Use appropriate animations that explain the concept.
13. DO NOT use the SVG transform attribute anywhere.
14. DO NOT use CSS transforms.
15. Position shapes directly using x, y, cx and cy coordinates.
16. Keep all shapes and labels within 800x500.
17. Avoid nested transformed groups.

VISUAL QUALITY:
- Clean educational textbook-style layout.
- Generous spacing between labels and shapes.
- Minimum font size of 13px for normal labels.
- Never overlap text.
- Use a clear visual hierarchy.
- Avoid unnecessary decorative elements.

Return the complete SVG starting with <svg
and ending with </svg>.
"""

    # --------------------------------------------------
    # SPECIAL INSTRUCTIONS: PARTS OF A CIRCLE
    # --------------------------------------------------

    if "circle" in concept.lower():

        prompt += """

SPECIAL INSTRUCTIONS FOR PARTS OF A CIRCLE:

Create a large, mathematically accurate circle diagram.

Clearly identify:
1. Centre - exact centre marked with a dot.
2. Radius - line from centre to circumference.
3. Diameter - line through the exact centre connecting
   opposite points on the circumference.
4. Chord - separate line connecting two circumference points
   without passing through the centre.
5. Circumference - outer circular boundary.

LAYOUT:
- One large circle in the central area.
- Different colours for radius, diameter and chord.
- Labels in separate positions with leader lines.
- Circumference label outside the circle.
- Title at the top.
- Formulas below the circle:
  Diameter = 2 x Radius
  Radius = Diameter / 2

MATHEMATICAL ACCURACY:
- Diameter passes through the exact centre.
- Radius is exactly half the diameter.
- Chord endpoints lie on the circumference.
- Chord must not be confused with diameter.
- Circumference is the boundary, not the interior area.

Prioritise readability and accuracy.
"""

    # --------------------------------------------------
    # SPECIAL INSTRUCTIONS: STATES OF MATTER
    # --------------------------------------------------

    if all(word in concept.lower() for word in ("solid", "liquid", "gas")):

        prompt += """

==================================================
SPECIAL INSTRUCTIONS: STATES OF MATTER
==================================================

Create an educational comparison of SOLID, LIQUID and GAS.

IMPORTANT:
The three states must have visibly different particle
arrangements and physically appropriate containers.

Use three clearly separated sections:
1. SOLID
2. LIQUID
3. GAS

Do NOT use three identical rectangular boxes.
The LIQUID section MUST use an open-top beaker.

------------------------------
1. SOLID: FIXED, VIBRATING PARTICLES
------------------------------

PARTICLE ARRANGEMENT:

- Draw at least 45 individual circular particles.
- Arrange them in a dense, orderly crystal lattice.
- Use approximately 7 columns and 7 rows.
- Particles must be almost touching.
- Use consistent particle sizes.
- Fill most of the available interior space.
- Keep very small, uniform gaps.
- Every particle should have the same colour.
- Do not highlight one particle in a different colour.
- Do not create one special central particle.

ANIMATION - EXTREMELY IMPORTANT:

- ALL solid particles must vibrate.
- Every individual particle must have its own subtle
  vibration around its original fixed position.
- Use tiny alternating movements of approximately 1 pixel.
- Each particle must return to its original position.
- Use gentle horizontal and vertical vibration.
- Stagger the timing slightly between particles if needed.
- Keep every particle in its original lattice location.
- Particles must never travel across the container.
- No particle may bounce vertically over a noticeable distance.
- Do not animate only one particle.
- Do not animate just the centre particle.
- Do not animate the entire solid group as one moving object.
- Do not use a single travelling particle to represent vibration.

Prefer individual SVG SMIL animations on the circles,
using their cx and cy attributes.
Do not use CSS transforms.

The final appearance must clearly show a dense solid lattice
with all particles vibrating subtly in place.

------------------------------
2. LIQUID: OPEN-TOP BEAKER
------------------------------

THIS SECTION MUST LOOK LIKE A REAL LIQUID IN A BEAKER.

CONTAINER SHAPE:

- Draw a transparent, open-top laboratory beaker.
- The beaker must have a clearly visible open rim.
- Draw two side walls extending downwards.
- Draw a curved or rounded bottom connecting the side walls.
- Use a flat-bottom or gently curved-bottom beaker.
- The container must NOT be a rectangular box.
- Do not draw a closed rectangle around the liquid.
- Make the beaker outline visibly different from the solid
  and gas containers.
- Use a light blue or pale cyan liquid appearance.

PARTICLE ARRANGEMENT:

- Draw at least 30 individual circular particles.
- Keep particles close together but irregularly arranged.
- Put particles only inside the lower portion of the beaker.
- Spread particles across the full width of the beaker bottom.
- Follow the beaker's side walls and bottom shape.
- The particles must form a visible liquid body.
- Create a clear, nearly horizontal upper liquid surface.
- Leave visible empty space above the liquid.
- Do not arrange the particles in a regular grid.
- Do not create a circular cluster in the centre.
- Do not let particles float above the liquid surface.
- Do not place particles outside the beaker.

ANIMATION:

- Liquid particles should move gently and locally.
- They may slide past neighbouring particles.
- Keep particles close to one another.
- Do not make them bounce high into the empty space.
- Do not let particles escape the beaker.
- Show motion without destroying the overall liquid shape.

The viewer must immediately recognise that the liquid
takes the shape of the bottom of its beaker.

------------------------------
3. GAS: WIDELY SPACED PARTICLES
------------------------------

CONTAINER:

- Draw a clearly outlined gas container.
- A simple rectangular container is acceptable.

PARTICLE ARRANGEMENT:

- Draw at least 15 individual circular particles.
- Spread them throughout the entire available interior.
- Leave large gaps between particles.
- Use an irregular distribution.
- Do not cluster particles together.
- Make the particles visibly farther apart than in the solid
  and liquid sections.

ANIMATION:

- Animate particles moving in different directions.
- Use gentle, independent movement.
- Keep every particle inside the container.
- Gas particles must move more freely than solid and liquid
  particles.

------------------------------
OVERALL SVG LAYOUT
------------------------------

- Use a clean landscape layout.
- Place STATES OF MATTER as the main title at the top.
- Place SOLID, LIQUID and GAS as clear section headings.
- Use enough horizontal spacing to distinguish all sections.
- Make the liquid beaker visually obvious.
- Make all three particle arrangements large enough to inspect.
- Use readable labels and short explanations.

Include these explanations:

SOLID:
"Tightly packed particles; vibrate in fixed positions."

LIQUID:
"Close particles; slide past one another."

GAS:
"Far apart particles; move freely in all directions."

Use consistent particle sizes across all three states.

------------------------------
FINAL SCIENTIFIC CHECK
------------------------------

Before returning the SVG, check the following:

1. Are ALL solid particles vibrating subtly?
2. Are solid particles staying near their original positions?
3. Is there NO single central particle bouncing up and down?
4. Is the solid arrangement dense and orderly?
5. Is the liquid inside a genuine open-top beaker?
6. Does the liquid occupy the lower portion of that beaker?
7. Does the liquid spread across the beaker bottom?
8. Is there a visible horizontal liquid surface?
9. Are gas particles widely separated throughout their container?
10. Are all three states visually distinguishable?

If any answer is NO, correct the diagram before returning it.

Scientific accuracy and visual clarity are more important
than decorative animation.

Return ONLY the complete SVG.
"""

    # --------------------------------------------------
    # VALIDATION CORRECTION PROMPT
    # --------------------------------------------------

    if correction:

        prompt += f"""

YOUR PREVIOUS SVG FAILED VALIDATION.

Fix these problems:
{correction}

Return a completely corrected SVG.
"""

    return prompt


# --------------------------------------------------
# SVG EXTRACTION
# --------------------------------------------------

def extract_svg(response_text):
    """Extract the SVG element from Gemini's response."""

    match = re.search(
        r"<svg\b.*?</svg>",
        response_text,
        flags=re.DOTALL | re.IGNORECASE
    )

    if not match:
        raise ValueError("Gemini did not return a valid SVG element.")

    return match.group(0).strip()


# --------------------------------------------------
# COST CALCULATION
# --------------------------------------------------

def calculate_cost(input_tokens, output_tokens):
    """Estimate cost using configured reference pricing."""

    input_cost = (
        input_tokens / 1_000_000
    ) * INPUT_PRICE_PER_MILLION

    output_cost = (
        output_tokens / 1_000_000
    ) * OUTPUT_PRICE_PER_MILLION

    return round(input_cost + output_cost, 8)


# --------------------------------------------------
# API ERROR HANDLING
# --------------------------------------------------

def is_retryable_error(error):
    """Identify temporary API errors."""

    status_code = (
        getattr(error, "code", None)
        or getattr(error, "status_code", None)
    )

    if callable(status_code):
        status_code = status_code()

    if status_code in (429, 503):
        return True

    error_text = str(error).lower()

    return (
        "429" in error_text
        or "503" in error_text
        or "resource_exhausted" in error_text
        or "service_unavailable" in error_text
    )


# --------------------------------------------------
# GEMINI SVG GENERATION
# --------------------------------------------------

def generate_svg(concept, correction=None):
    """
    Generate one animated SVG.

    Handles up to 3 retries for temporary API errors.
    Returns SVG, token usage, estimated cost and retry count.
    """

    prompt = build_prompt(concept, correction)

    api_retries = 0
    max_retries = 3

    while True:

        try:

            response = client.models.generate_content(
                model=MODEL_NAME,
                contents=prompt
            )

            if not response.text:
                raise ValueError("Gemini returned an empty response.")

            svg = extract_svg(response.text)

            usage = response.usage_metadata

            input_tokens = (
                getattr(usage, "prompt_token_count", 0) or 0
            ) if usage else 0

            output_tokens = (
                getattr(usage, "candidates_token_count", 0) or 0
            ) if usage else 0

            return {
                "svg": svg,
                "model": MODEL_NAME,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "estimated_cost_usd": calculate_cost(
                    input_tokens,
                    output_tokens
                ),
                "api_retries": api_retries
            }

        except Exception as error:

            if is_retryable_error(error) and api_retries < max_retries:

                api_retries += 1
                wait_time = 2 ** api_retries

                print(
                    f"Temporary Gemini API error. "
                    f"Retry {api_retries}/{max_retries} "
                    f"after {wait_time} seconds."
                )

                time.sleep(wait_time)
                continue

            raise RuntimeError(
                f"Gemini generation failed: {error}"
            ) from error

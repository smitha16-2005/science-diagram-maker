# AI-Powered Science Diagram Maker

An AI-powered web application that generates animated SVG diagrams for five science concepts, validates them programmatically, and allows a human reviewer to approve or reject each diagram with feedback.

## Features

- Generates animated SVG diagrams using Google's Gemini API.
- Supports five concepts:
  - Pythagoras Theorem
  - Parts of a Circle
  - Series Circuit
  - Photosynthesis
  - States of Matter
- Automatically validates generated SVGs.
- Retries generation once when validation fails, including correction feedback in the next prompt.
- Handles temporary Gemini API errors (429 and 503) with retries.
- Tracks model name, token usage, estimated API cost, and retry counts.
- Provides an interactive dashboard with animated diagrams.
- Supports human approval/rejection and reviewer notes.
- Saves generated results and review feedback in `data/results.json`.

## Tech Stack

**Backend:** Python, FastAPI, Uvicorn  
**AI:** Google Gemini API  
**Frontend:** HTML, CSS, JavaScript  
**SVG Validation:** XML parsing, svgpathtools  
**Storage:** JSON file

## Validation

Each generated SVG is checked for:

1. Valid XML and SVG root element.
2. Supported SVG geometry staying within the viewBox.
3. Presence of a title.
4. At least three text labels.
5. Presence of animation.
6. Presence of graphical elements (custom check).

The application retries SVG generation once if validation fails. The correction prompt includes the validation errors.

The viewBox validator checks supported geometry, including path bounding boxes. Elements with explicit transforms are conservatively rejected because transformed coordinate calculations are not implemented.

## Final Results

| Concept | Validation | Estimated Cost (USD) | API Retries | Validation Retries |
|---|---|---:|---:|---:|
| Pythagoras Theorem | PASS | $0.0091271 | 0 | 0 |
| Parts of a Circle | PASS | $0.0051315 | 0 | 0 |
| Series Circuit | PASS | $0.0052026 | 0 | 0 |
| Photosynthesis | PASS | $0.0085227 | 0 | 0 |
| States of Matter | PASS | $0.0171860 | 0 | 1 |
| **Total** | **5/5 PASS** | **$0.0451699** | **0** | **1** |

Costs are estimates calculated from token usage and the reference rates configured in the application. They are not confirmed billing amounts.

## Local Setup

### 1. Clone the repository

```bash
git clone https://github.com/smitha16-2005/science-diagram-maker.git
cd science-diagram-maker
```

### 2. Create and activate a virtual environment

Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

Create a `.env` file in the project root:

```env
GEMINI_API_KEY=your_gemini_api_key
GEMINI_MODEL=gemini-3.5-flash-lite
```

Never commit your `.env` file or expose your API key.

### 5. Run the application

```bash
uvicorn main:app --reload
```

Open:

http://127.0.0.1:8000/

The dashboard loads the saved diagrams from `data/results.json`. Generating or regenerating a diagram makes a Gemini API request.

## What Failed and How It Was Fixed

- **SVG viewBox validation:** The initial implementation did not adequately check path geometry. Improved it using SVG path bounding-box calculations.
- **Circle diagram:** Initial labels overlapped. Improved the generation instructions to separate labels and clarify radius, diameter, chord, and circumference.
- **States of Matter:** The matter-specific prompt was not activated because the concept description did not contain the expected keyword. Corrected the prompt condition and strengthened the instructions for vibrating solid particles and liquid container shape.
- **Temporary API errors:** Added retry handling for Gemini 429 and 503 responses.
- **Review persistence:** Preserved existing reviewer decisions and notes when regenerating diagrams.

## What I Would Improve With One More Day

- Support full SVG transformation and coordinate calculations.
- Add stronger visual and semantic validation of scientific accuracy.
- Improve SVG sanitization and security before rendering generated SVG content.
- Move JSON-based storage to a persistent database.
- Add automated unit and integration tests.
- Improve accessibility and responsive dashboard design.

## AI Tools Used

- **Google Gemini API:** Used to generate animated SVG diagrams from concept-specific prompts.
- **ChatGPT:** Used for implementation guidance, debugging, improving prompts, strengthening SVG validation, and understanding the code.

The application logic, validation process, and generated results were tested locally. AI-generated diagrams are programmatically validated, with human review available through the dashboard.
"""
Synthetic training data generator for fashion domain finetuning.

Generates training pairs for all 4 model roles:
1. Intent Classifier — (message, intent+params) pairs
2. Design Agent — (prompt, detailed_design_json) pairs
3. Tailor Agent — (query, tailoring_guide_json) pairs
4. Style Agent — (question, advice_response) pairs

Outputs in ShareGPT format for Unsloth compatibility.
"""
from __future__ import annotations

import json
import random
import uuid
from pathlib import Path
from typing import Any

# ── Seed Data ────────────────────────────────────────────────────────
OCCASIONS = [
    "wedding", "sangeet", "mehendi", "reception", "haldi",
    "engagement", "anniversary", "birthday party", "office",
    "casual outing", "temple visit", "pooja", "Diwali",
    "Holi", "Eid", "Christmas party", "New Year party",
    "date night", "college fest", "farewell", "graduation",
    "baby shower", "bridal shower", "cocktail party", "lunch meeting",
]

GARMENT_TYPES = [
    "saree", "lehenga", "kurta", "sherwani", "salwar kameez",
    "anarkali", "sharara", "palazzo set", "dhoti kurta",
    "indo-western dress", "crop top lehenga", "pre-draped saree",
    "pant saree", "jacket lehenga", "ruffle saree",
    "pathani suit", "nehru jacket", "bandgala", "jodhpuri suit",
    "kurti", "straight kurta", "A-line kurta", "angrakha kurta",
]

FABRICS = [
    "Banarasi silk", "Kanjeevaram silk", "raw silk", "art silk",
    "chanderi", "cotton", "linen", "georgette", "chiffon",
    "crepe", "velvet", "organza", "net", "tussar silk",
    "Pochampally ikat", "Patola", "Bandhani", "Kalamkari",
    "khadi", "muslin", "satin", "brocade", "jacquard",
]

COLORS = [
    "red", "maroon", "burgundy", "wine", "coral",
    "pink", "blush pink", "hot pink", "magenta", "rose gold",
    "blue", "navy blue", "royal blue", "powder blue", "teal",
    "green", "emerald", "sage green", "olive", "mint",
    "yellow", "mustard", "gold", "champagne", "ivory",
    "purple", "lavender", "plum", "violet", "mauve",
    "orange", "peach", "rust", "terracotta", "burnt orange",
    "black", "white", "off-white", "cream", "beige", "grey",
]

BODY_TYPES = ["pear", "apple", "hourglass", "rectangle", "inverted triangle"]
CULTURAL_CONTEXTS = [
    "South Indian", "North Indian", "Bengali", "Rajasthani",
    "Punjabi", "Hyderabadi", "Gujarati", "Maharashtrian",
    "Kashmiri", "Kerala", "Tamil", "Telugu", "Marathi",
]

EMBELLISHMENTS = [
    "zari work", "thread embroidery", "mirror work", "sequin work",
    "stone work", "kundan work", "gota patti", "chikankari",
    "phulkari", "kasuti", "kantha", "aari work", "pearl work",
    "cutdana", "dabka", "resham", "zardozi", "mukaish",
]

BUDGETS = [
    "under ₹1,000", "₹1,000-₹3,000", "₹3,000-₹5,000",
    "₹5,000-₹10,000", "₹10,000-₹25,000", "₹25,000-₹50,000",
    "₹50,000-₹1,00,000", "above ₹1,00,000",
]


# ── Generators ───────────────────────────────────────────────────────

def generate_intent_pairs(count: int = 500) -> list[dict]:
    """Generate (message, classification) pairs for intent classifier training."""
    pairs = []

    templates = {
        "greeting": [
            "Hi", "Hello", "Hey there", "Good morning", "Namaste",
            "Hi, I need help with fashion", "Hello! What can you do?",
            "Namaskar", "Hey, I'm looking for outfit ideas",
            "Hi there! I have a wedding coming up",
        ],
        "design_request": [
            "Design a {color} {garment} for {occasion}",
            "I want a {garment} in {fabric} for my {occasion}",
            "Create a {cultural} style {garment} with {embellishment}",
            "Can you design something for {occasion}? I prefer {color}",
            "I need a {garment} outfit. Budget is {budget}",
            "Show me a {color} {garment} design with {embellishment}",
            "Design a bridal {garment} in {fabric} with heavy {embellishment}",
            "I want something unique for my {occasion}. Think {cultural} meets modern",
        ],
        "product_search": [
            "Find me {color} {garment} under {budget}",
            "Show me {garment} options for {occasion}",
            "Where can I buy {fabric} {garment}?",
            "Search for {color} {garment} from good brands",
            "I want to buy a {garment}. Budget {budget}",
            "Show me affordable {garment} options for {occasion}",
        ],
        "style_advice": [
            "What should I wear to a {occasion}?",
            "What colors suit {body_type} body type?",
            "Is {color} good for {occasion}?",
            "What {garment} style flatters {body_type} figure?",
            "Help me choose between {garment} and {garment2} for {occasion}",
            "What's trending in {cultural} fashion?",
            "How to accessorize a {color} {garment}?",
        ],
        "tailoring": [
            "How much fabric for a {garment}?",
            "Tailoring instructions for {garment} in {fabric}",
            "What's the yardage needed for a {garment}?",
            "Stitching guide for {garment} with {embellishment}",
            "How to stitch a {garment} blouse?",
            "Measurement guide for {garment}",
        ],
        "body_scan": [
            "I want to scan my body", "How to upload body photos?",
            "Set up my avatar", "Take my measurements",
            "I want to create my 3D model", "How does body scanning work?",
        ],
        "virtual_tryon": [
            "Try this on my avatar", "Show me how this looks on me",
            "Virtual try-on for this design", "Can I see this on my body?",
            "Preview this outfit on me",
        ],
        "wardrobe_manage": [
            "Add this to my wardrobe", "What's in my closet?",
            "Show my wardrobe", "I want to organize my clothes",
            "Suggest an outfit from my wardrobe for {occasion}",
        ],
        "feedback": [
            "I love this design!", "This is not what I wanted",
            "Can you change the color to {color}?",
            "Perfect! Save this design", "I don't like this, try again",
            "Rate: 4/5 — great but change the {embellishment}",
        ],
        "general_chat": [
            "What's the difference between {fabric} and {fabric2}?",
            "History of {garment} in Indian fashion",
            "How to care for {fabric} garments?",
            "What's {embellishment}?",
            "Tell me about {cultural} wedding traditions",
        ],
    }

    for _ in range(count):
        intent = random.choice(list(templates.keys()))
        template = random.choice(templates[intent])

        # Fill template variables
        msg = template.format(
            color=random.choice(COLORS),
            garment=random.choice(GARMENT_TYPES),
            garment2=random.choice(GARMENT_TYPES),
            occasion=random.choice(OCCASIONS),
            fabric=random.choice(FABRICS),
            fabric2=random.choice(FABRICS),
            cultural=random.choice(CULTURAL_CONTEXTS),
            embellishment=random.choice(EMBELLISHMENTS),
            budget=random.choice(BUDGETS),
            body_type=random.choice(BODY_TYPES),
        )

        params = {}
        if "{occasion}" in template or "occasion" in template.lower():
            params["occasion"] = random.choice(OCCASIONS)
        if "{garment}" in template:
            params["garment_type"] = random.choice(GARMENT_TYPES)
        if "{color}" in template:
            params["colors"] = [random.choice(COLORS)]
        if "{budget}" in template:
            params["budget"] = random.choice(BUDGETS)
        if "{body_type}" in template:
            params["body_type"] = random.choice(BODY_TYPES)

        classification = {
            "intent": intent,
            "confidence": round(random.uniform(0.85, 0.99), 2),
            "language": random.choice(["en", "en", "en", "hi", "te"]),
            "parameters": params,
        }

        pairs.append({
            "conversations": [
                {"from": "system", "value": "Classify the user's fashion-related message into an intent category and extract parameters. Respond with JSON."},
                {"from": "human", "value": msg},
                {"from": "gpt", "value": json.dumps(classification)},
            ]
        })

    return pairs


def generate_design_pairs(count: int = 300) -> list[dict]:
    """Generate (design_request, design_response) pairs for design agent training."""
    pairs = []

    for _ in range(count):
        occasion = random.choice(OCCASIONS)
        garment = random.choice(GARMENT_TYPES)
        color = random.choice(COLORS)
        fabric = random.choice(FABRICS)
        cultural = random.choice(CULTURAL_CONTEXTS)
        embellish = random.choice(EMBELLISHMENTS)
        body = random.choice(BODY_TYPES)

        prompt = f"Design a {color} {garment} in {fabric} for {occasion}. Body type: {body}. Cultural style: {cultural}."

        response = {
            "description": f"A stunning {color} {garment} crafted in luxurious {fabric}, perfect for {occasion}. "
                          f"Featuring exquisite {embellish} along the borders and bodice, this {cultural}-inspired piece "
                          f"is designed to flatter a {body} body type with its carefully proportioned silhouette.",
            "sdxl_prompt": f"{color} {garment}, {fabric} fabric, {embellish} embellishment, {cultural} style, "
                          f"professional fashion photography, studio lighting, detailed fabric texture, "
                          f"elegant {occasion} outfit, high fashion editorial, 4k quality",
            "fabric_notes": f"Recommended: {fabric} (120 GSM for drape and flow). "
                           f"Lining: cotton silk for comfort. "
                           f"Interfacing: fusible non-woven for structured areas.",
            "cost_range": f"₹{random.randint(3,15)*1000:,} - ₹{random.randint(15,50)*1000:,}",
            "alternatives": [
                f"Similar design in {random.choice(COLORS)} {random.choice(FABRICS)}",
                f"Contemporary version with {random.choice(EMBELLISHMENTS)} detailing",
            ],
            "accessories": [
                f"{random.choice(['Kundan', 'Polki', 'Temple', 'Pearl'])} jewelry set",
                f"{random.choice(['Potli bag', 'Clutch', 'Sling bag'])} in matching {color}",
                f"{random.choice(['Juttis', 'Heels', 'Kolhapuris', 'Block heels'])}",
            ],
        }

        pairs.append({
            "conversations": [
                {"from": "system", "value": "You are an expert Indian fashion designer. Create detailed outfit designs with construction notes."},
                {"from": "human", "value": prompt},
                {"from": "gpt", "value": json.dumps(response, indent=2)},
            ]
        })

    return pairs


def generate_tailor_pairs(count: int = 200) -> list[dict]:
    """Generate tailoring guide training pairs."""
    pairs = []

    yardage_map = {
        "saree blouse": (1.0, 0.5), "lehenga": (6.0, 3.0), "kurta": (2.5, 1.5),
        "sherwani": (4.0, 2.5), "salwar kameez": (4.5, 2.0), "anarkali": (5.0, 3.0),
        "sharara": (5.5, 2.5), "palazzo set": (4.0, 2.0), "dhoti kurta": (5.0, 2.0),
        "kurti": (2.0, 1.0), "nehru jacket": (2.0, 1.0), "bandgala": (3.5, 2.0),
    }

    for _ in range(count):
        garment = random.choice(list(yardage_map.keys()))
        fabric = random.choice(FABRICS)
        main_yardage, lining_yardage = yardage_map.get(garment, (3.0, 1.5))
        main_yardage += random.uniform(-0.5, 0.5)

        response = {
            "garment": garment.title(),
            "fabric_recommendation": f"{fabric} ({random.randint(80,200)} GSM)",
            "fabric_gsm": f"{random.randint(80,200)} GSM, {random.randint(40,80)} thread count",
            "yardage_meters": round(main_yardage, 1),
            "lining_meters": round(lining_yardage, 1),
            "interfacing_meters": round(random.uniform(0.3, 1.0), 1),
            "seam_allowance_cm": random.choice([1.0, 1.5, 2.0]),
            "construction_steps": [
                f"1. Take accurate body measurements (bust, waist, hips, length)",
                f"2. Draft pattern on brown paper with {random.choice([1.0, 1.5])}cm seam allowance",
                f"3. Cut {fabric} following grain line direction",
                f"4. Mark darts and notches with tailoring chalk",
                f"5. Stitch darts first, then side seams",
                f"6. Attach lining to main fabric",
                f"7. Finish neckline with facing or bias binding",
                f"8. Set sleeves and finish armholes",
                f"9. Hem bottom edge with blind stitch",
                f"10. Press all seams with appropriate iron settings",
                f"11. Add closures (hooks/buttons/zipper)",
                f"12. Final pressing and quality check",
            ],
            "iron_settings": random.choice([
                "Medium heat (150°C) with steam, press seams open",
                "Low heat (110°C) with press cloth for delicate fabric",
                "High heat (200°C) for cotton, use starch for crisp finish",
            ]),
            "finishing": random.choice([
                "French seams for unlined garments, overlocked edges for lined",
                "Bind all raw edges with matching bias tape",
                "Serge all seams, add interfacing to collar and cuffs",
            ]),
            "pro_tips": [
                f"Pre-wash {fabric} to account for 2-3% shrinkage",
                "Always cut on a flat surface, pin pattern firmly",
                "Test stitch on scrap fabric first to check tension",
                f"For {garment}, use a walking foot for even feeding",
            ],
            "estimated_tailoring_cost": f"₹{random.randint(5,25)*100} - ₹{random.randint(25,80)*100}",
            "difficulty_level": random.choice(["beginner", "intermediate", "advanced"]),
            "time_estimate_hours": random.randint(4, 24),
        }

        pairs.append({
            "conversations": [
                {"from": "system", "value": "You are a master Indian tailor. Provide detailed tailoring guides with exact measurements and construction steps."},
                {"from": "human", "value": f"How to stitch a {garment} in {fabric}?"},
                {"from": "gpt", "value": json.dumps(response, indent=2)},
            ]
        })

    return pairs


def generate_style_pairs(count: int = 200) -> list[dict]:
    """Generate style advice training pairs."""
    pairs = []

    for _ in range(count):
        body = random.choice(BODY_TYPES)
        occasion = random.choice(OCCASIONS)
        cultural = random.choice(CULTURAL_CONTEXTS)

        question = random.choice([
            f"What should a {body} body type wear to a {occasion}?",
            f"Best {cultural} outfit for {occasion}?",
            f"How to dress for a {occasion} if I'm {body} shaped?",
            f"Color recommendations for {body} body type attending a {occasion}?",
        ])

        garment_suggestions = random.sample(GARMENT_TYPES, 3)
        color_suggestions = random.sample(COLORS, 4)

        response = (
            f"For a {body} body type attending a {occasion}, I'd recommend:\n\n"
            f"✨ **Top Pick**: {garment_suggestions[0].title()} in {color_suggestions[0]}\n"
            f"A {garment_suggestions[0]} in {color_suggestions[0]} is perfect because it "
            f"{'elongates your silhouette' if body == 'pear' else 'balances your proportions'} "
            f"and is culturally appropriate for {occasion}.\n\n"
            f"🎨 **Color Palette**: {', '.join(color_suggestions[:3])}\n"
            f"These colors complement most Indian skin tones and are considered "
            f"{'auspicious' if occasion in ('wedding', 'pooja', 'Diwali') else 'stylish'} for {occasion}.\n\n"
            f"👗 **Alternatives**: {garment_suggestions[1].title()} or {garment_suggestions[2].title()}\n\n"
            f"💡 **Styling Tip**: Pair with {random.choice(EMBELLISHMENTS)} accessories for a "
            f"{'traditional' if cultural in ('South Indian', 'North Indian') else 'contemporary'} {cultural} look."
        )

        pairs.append({
            "conversations": [
                {"from": "system", "value": "You are an expert Indian fashion stylist. Give personalized style advice."},
                {"from": "human", "value": question},
                {"from": "gpt", "value": response},
            ]
        })

    return pairs


def generate_all_datasets(output_dir: str = "data/synthetic") -> dict[str, int]:
    """Generate all training datasets and save as JSONL."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    datasets = {
        "intent_classifier": generate_intent_pairs(500),
        "design_agent": generate_design_pairs(300),
        "tailor_agent": generate_tailor_pairs(200),
        "style_agent": generate_style_pairs(200),
    }

    counts = {}
    for name, data in datasets.items():
        filepath = output_path / f"{name}_train.jsonl"
        with open(filepath, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        counts[name] = len(data)
        print(f"✅ {name}: {len(data)} samples → {filepath}")

    # Also create a combined dataset
    combined = []
    for data in datasets.values():
        combined.extend(data)
    random.shuffle(combined)

    combined_path = output_path / "combined_train.jsonl"
    with open(combined_path, "w", encoding="utf-8") as f:
        for item in combined:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    counts["combined"] = len(combined)
    print(f"✅ combined: {len(combined)} samples → {combined_path}")

    return counts


if __name__ == "__main__":
    print("🔧 Generating synthetic training data...")
    counts = generate_all_datasets()
    print(f"\n📊 Total: {sum(counts.values())} training samples generated")
    print(f"   Intent Classifier: {counts['intent_classifier']}")
    print(f"   Design Agent: {counts['design_agent']}")
    print(f"   Tailor Agent: {counts['tailor_agent']}")
    print(f"   Style Agent: {counts['style_agent']}")

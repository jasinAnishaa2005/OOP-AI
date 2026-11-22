"""Deterministic offline generator for development and tests (no API key, no network)."""

import json

from app.ai.base import GenerationRequest, GenerationResponse, PlannedSlot


def _rubric(marks: int) -> list[dict]:
    first = max(1, marks // 2)
    items = [{"criterion": "Correct explanation of the core concept", "marks": first}]
    if marks - first:
        items.append({"criterion": "Accurate Java example and reasoning", "marks": marks - first})
    return items


def _java(slot: PlannedSlot) -> str:
    lines = [
        f"// Exam slot {slot.slot}: {slot.topic_name}",
        "public class Shape {",
        "    protected final String name;",
        "",
        "    public Shape(String name) {",
        "        this.name = name;",
        "    }",
        "",
        "    public double area() {",
        "        return 0;",
        "    }",
        "}",
        "",
        "class Circle extends Shape {",
        "    private final double r;",
        "",
        "    Circle(double r) {",
        '        super("circle");',
        "        this.r = r;",
        "    }",
        "",
        "    @Override",
        "    public double area() {",
        "        return Math.PI * r * r;",
        "    }",
        "}",
    ]
    return "\n".join(lines)


def fake_question(slot: PlannedSlot) -> dict:
    stem = f"[{slot.difficulty}] Question {slot.slot} on {slot.topic_name}: "
    base = {"slot": slot.slot}
    if slot.question_type == "mcq":
        return {
            **base,
            "question": stem + f"which statement about {slot.topic_name} is correct?",
            "options": [
                f"{slot.topic_name} is applied as described in option A",
                f"{slot.topic_name} never applies to Java classes",
                f"{slot.topic_name} only applies to primitive types",
                f"{slot.topic_name} is unrelated to object-oriented design",
            ],
            "correct_option": 0,
            "explanation": f"Option A reflects how {slot.topic_name} is used in object-oriented Java code.",
        }
    if slot.question_type == "theory":
        return {
            **base,
            "question": stem + f"explain {slot.topic_name} with a Java example.",
            "model_answer": f"{slot.topic_name} is explained here with a definition, its purpose and a Java example.",
            "key_points": [f"Definition of {slot.topic_name}", "Purpose and benefits", "Java example"],
            "rubric": _rubric(slot.marks),
        }
    if slot.question_type == "code_analysis":
        return {
            **base,
            "question": stem + f"analyse the code below with respect to {slot.topic_name}.",
            "code": _java(slot),
            "expected_answer": f"The code shows {slot.topic_name}: Circle overrides area() from Shape.",
            "rubric": _rubric(slot.marks),
        }
    return {
        **base,
        "question": stem + f"write Java code that demonstrates {slot.topic_name}.",
        "starter_code": "public class Solution {\n    // TODO\n}",
        "reference_solution": _java(slot),
        "test_cases": [
            {"name": "basic", "description": "Typical input", "expected": "Correct result"},
            {"name": "edge", "description": "Edge case input", "expected": "Handled without errors"},
        ],
        "rubric": _rubric(slot.marks),
    }


class FakeGenerator:
    provider = "fake"
    model = "fake-exam-generator"

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        payload = {"questions": [fake_question(slot) for slot in request.slots]}
        return GenerationResponse(text=json.dumps(payload), input_tokens=0, output_tokens=0)

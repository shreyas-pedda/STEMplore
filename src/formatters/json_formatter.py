def format_questions(raw_questions):
    """
    Converts raw question dicts into STEMplore-compatible JSON.
    Ensures:
        - type = "SELECT"
        - correct order numbers
        - exactly 4 options per question
        - exactly one correct option
    """
    formatted_questions = []

    for i, q in enumerate(raw_questions):
        
        question_text = str(q.get("question", "")).strip()
        options = q.get("challenge_options", q.get("choices", []))  # support either field
        if len(options) != 4:
            raise ValueError(f"Question {i+1} must have exactly 4 options.")

        # Can only have 1 correct answer
        correct_count = sum(1 for opt in options if opt.get("correct", False))
        if correct_count != 1:
            raise ValueError(f"Question {i+1} must have exactly one correct answer.")

        # Build options
        formatted_options = []
        for opt in options:
            formatted_options.append({
                "text": str(opt.get("text", "")).strip(),
                "correct": bool(opt.get("correct", False)),
                "imageSrc": opt.get("imageSrc")  # include if present
            })

        # Build question
        formatted_questions.append({
            "type": "SELECT",
            "question": question_text,
            "order": i + 1,
            "challenge_options": formatted_options,
            "imageSrc": q.get("imageSrc")  # optional
        })

    return formatted_questions
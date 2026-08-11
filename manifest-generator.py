import json
from pathlib import Path


# ============================================================
# Configuration
# ============================================================

ROOT_DIR = Path(__file__).resolve().parent
CONTENT_DIR = ROOT_DIR / "content"
MANIFEST_FILE = ROOT_DIR / "manifest.json"

IMAGE_EXTENSIONS = {
    ".webp",
    ".png",
    ".jpg",
    ".jpeg",
}


# ============================================================
# Terminal helpers
# ============================================================

def info(message):
    print(f"✓ {message}")


def warning(message):
    print(f"⚠ {message}")


def error(message):
    print(f"✗ {message}")


# ============================================================
# Filename helpers
# ============================================================

def parse_lesson_filename(filename):
    """
    Expected:

        lessonid.topic.course.version.json

    Example:

        newtons-laws.mechanics.phy-102.1.json

    Returns:

        (lessonid, topic, course, version)

    or None if invalid.
    """

    if not filename.lower().endswith(".json"):
        return None

    name = filename[:-5]

    parts = name.split(".")

    if len(parts) != 4:
        return None

    lessonid, topic, course, version = parts

    if not lessonid or not topic or not course:
        return None

    if not version.isdigit():
        return None

    version = int(version)

    if version < 1:
        return None

    return (
        lessonid,
        topic,
        course,
        version,
    )


def parse_image_filename(filename):
    """
    Recognizes:

        image.course.webp
        image.course.png
        image.course.jpg
        image.course.jpeg

    and:

        image.topic.course.webp
        image.topic.course.png
        image.topic.course.jpg
        image.topic.course.jpeg

    Returns:

        ("course", course)

    or:

        ("topic", topic, course)

    or None.
    """

    path = Path(filename)

    if path.suffix.lower() not in IMAGE_EXTENSIONS:
        return None

    parts = path.stem.split(".")

    if len(parts) == 2 and parts[0] == "image":
        return (
            "course",
            parts[1],
        )

    if len(parts) == 3 and parts[0] == "image":
        return (
            "topic",
            parts[1],
            parts[2],
        )

    return None


# ============================================================
# Manifest helpers
# ============================================================

def load_existing_manifest():
    """
    Load the existing manifest.

    If it doesn't exist or cannot be read,
    start from version 1.
    """

    if not MANIFEST_FILE.exists():
        return {
            "version": 1,
            "courses": [],
        }

    try:

        with MANIFEST_FILE.open(
            "r",
            encoding="utf-8",
        ) as file:

            manifest = json.load(file)

        if not isinstance(manifest, dict):
            raise ValueError(
                "Manifest root must be an object."
            )

        version = manifest.get(
            "version",
            1,
        )

        courses = manifest.get(
            "courses",
            [],
        )

        if not isinstance(version, int):
            warning(
                "Existing manifest has an "
                "invalid version. Using 1."
            )

            version = 1

        if not isinstance(courses, list):
            warning(
                "Existing manifest has an "
                "invalid courses field. "
                "Using an empty list."
            )

            courses = []

        return {
            "version": version,
            "courses": courses,
        }

    except Exception as exc:

        warning(
            f"Unable to read existing manifest: "
            f"{exc}"
        )

        warning(
            "A new manifest will be generated."
        )

        return {
            "version": 1,
            "courses": [],
        }


# ============================================================
# Main generator
# ============================================================

def main():

    print()
    print("========================================")
    print("      DENDRILL MANIFEST GENERATOR")
    print("========================================")
    print()

    if not CONTENT_DIR.exists():

        error(
            f"Content directory not found: "
            f"{CONTENT_DIR}"
        )

        return 1

    courses = {}

    malformed_files = 0
    warning_count = 0

    # --------------------------------------------------------
    # Scan content directory
    # --------------------------------------------------------

    files = [
        file
        for file in CONTENT_DIR.rglob("*")
        if file.is_file()
    ]

    print(
        f"Scanning {len(files)} files..."
    )

    print()

    # --------------------------------------------------------
    # First pass:
    # discover images
    # --------------------------------------------------------

    for file in files:

        filename = file.name

        parsed = parse_image_filename(
            filename
        )

        if not parsed:
            continue

        relative_path = file.relative_to(
            CONTENT_DIR
        ).as_posix()

        # ----------------------------------------------------
        # Course image
        # ----------------------------------------------------

        if parsed[0] == "course":

            _, course = parsed

            if course not in courses:

                courses[course] = {
                    "image": "",
                    "topics": {},
                }

            if courses[course]["image"]:

                warning(
                    f"Duplicate course image "
                    f"for: {course}"
                )

                warning_count += 1

            courses[course]["image"] = (
                relative_path
            )

            info(
                f"Course image found: "
                f"{course} → {relative_path}"
            )

        # ----------------------------------------------------
        # Topic image
        # ----------------------------------------------------

        elif parsed[0] == "topic":

            _, topic, course = parsed

            if course not in courses:

                courses[course] = {
                    "image": "",
                    "topics": {},
                }

            if topic not in courses[
                course
            ]["topics"]:

                courses[
                    course
                ]["topics"][topic] = {
                    "image": "",
                    "lessons": [],
                }

            if courses[course][
                "topics"
            ][topic]["image"]:

                warning(
                    f"Duplicate topic image "
                    f"for: "
                    f"{topic}.{course}"
                )

                warning_count += 1

            courses[course][
                "topics"
            ][topic]["image"] = (
                relative_path
            )

            info(
                f"Topic image found: "
                f"{topic}.{course} "
                f"→ {relative_path}"
            )

    # --------------------------------------------------------
    # Second pass:
    # discover lessons
    # --------------------------------------------------------

    for file in files:

        filename = file.name

        # Ignore non-JSON files.
        if file.suffix.lower() != ".json":
            continue

        # Ignore manifest.json.
        if filename == "manifest.json":
            continue

        parsed = parse_lesson_filename(
            filename
        )

        if not parsed:

            malformed_files += 1

            error(
                f"Invalid lesson filename: "
                f"{filename}"
            )

            continue

        (
            lessonid,
            topic,
            course,
            version,
        ) = parsed

        # ----------------------------------------------------
        # Create course
        # ----------------------------------------------------

        if course not in courses:

            courses[course] = {
                "image": "",
                "topics": {},
            }

        # ----------------------------------------------------
        # Create topic
        # ----------------------------------------------------

        if topic not in courses[
            course
        ]["topics"]:

            courses[
                course
            ]["topics"][topic] = {
                "image": "",
                "lessons": [],
            }

        topic_data = courses[
            course
        ]["topics"][topic]

        # ----------------------------------------------------
        # Check duplicate lesson IDs
        # ----------------------------------------------------

        existing_lessons = {
            lesson["lessonid"]
            for lesson in topic_data[
                "lessons"
            ]
        }

        if lessonid in existing_lessons:

            error(
                f"Duplicate lesson: "
                f"{lessonid}.{topic}.{course}"
            )

            continue

        # ----------------------------------------------------
        # Add lesson
        # ----------------------------------------------------

        topic_data[
            "lessons"
        ].append(
            {
                "lessonid": lessonid,
                "version": version,
            }
        )

        info(
            f"Lesson found: "
            f"{lessonid} "
            f"(v{version}) "
            f"({topic} / {course})"
        )

    # ========================================================
    # Build courses structure
    # ========================================================

    generated_courses = []

    for course in sorted(courses):

        course_data = courses[course]

        course_image = course_data[
            "image"
        ]

        if not course_image:

            warning(
                f"No image found for "
                f"course: {course}"
            )

            warning_count += 1

        generated_topics = []

        for topic in sorted(
            course_data["topics"]
        ):

            topic_data = course_data[
                "topics"
            ][topic]

            topic_image = topic_data[
                "image"
            ]

            if not topic_image:

                warning(
                    f"No image found for "
                    f"topic: "
                    f"{topic}.{course}"
                )

                warning_count += 1

            lessons = sorted(
                topic_data["lessons"],
                key=lambda lesson:
                    lesson["lessonid"],
            )

            generated_topics.append(
                {
                    "topic": topic,
                    "Image": topic_image,
                    "content": lessons,
                }
            )

        generated_courses.append(
            {
                "course": course,
                "Image": course_image,
                "content": generated_topics,
            }
        )

    # ========================================================
    # Load existing manifest
    # ========================================================

    existing_manifest = (
        load_existing_manifest()
    )

    existing_courses = (
        existing_manifest["courses"]
    )

    existing_version = (
        existing_manifest["version"]
    )

    # ========================================================
    # Compare content
    # ========================================================

    content_changed = (
        generated_courses
        != existing_courses
    )

    # ========================================================
    # No changes
    # ========================================================

    if not content_changed:

        print()
        print(
            "========================================"
        )
        print(
            "          NO CHANGES DETECTED"
        )
        print(
            "========================================"
        )
        print()

        info(
            f"Manifest remains at "
            f"version {existing_version}."
        )

        info(
            "manifest.json was not rewritten."
        )

        print()

        return 0

    # ========================================================
    # Changes detected
    # ========================================================

    new_version = (
        existing_version + 1
    )

    new_manifest = {
        "version": new_version,
        "courses": generated_courses,
    }

    # ========================================================
    # Write manifest
    # ========================================================

    with MANIFEST_FILE.open(
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            new_manifest,
            file,
            indent=2,
            ensure_ascii=False,
        )

        file.write("\n")

    # ========================================================
    # Statistics
    # ========================================================

    course_count = len(
        generated_courses
    )

    topic_count = sum(
        len(course["content"])
        for course in generated_courses
    )

    lesson_count = sum(
        len(topic["content"])
        for course in generated_courses
        for topic in course["content"]
    )

    # ========================================================
    # Output
    # ========================================================

    print()
    print(
        "========================================"
    )
    print(
        "       MANIFEST UPDATED"
    )
    print(
        "========================================"
    )
    print()

    info(
        f"Manifest version: "
        f"{existing_version} → {new_version}"
    )

    info(
        f"Courses: {course_count}"
    )

    info(
        f"Topics: {topic_count}"
    )

    info(
        f"Lessons: {lesson_count}"
    )

    if malformed_files:

        warning(
            f"Malformed files: "
            f"{malformed_files}"
        )

    if warning_count:

        warning(
            f"Warnings: {warning_count}"
        )

    else:

        info(
            "Warnings: 0"
        )

    print()

    info(
        f"Output: {MANIFEST_FILE}"
    )

    print()

    return 0


# ============================================================
# Entry point
# ============================================================

if __name__ == "__main__":
    raise SystemExit(main())
"""The initial OOC syllabus: 12 categories -> chapters -> topics.

Topic names follow the project specification exactly. Chapters group the specification's flat
lists so whole chapters can be selected; administrators can rename or reorganise them later.
"""

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Topic, TopicCategory, TopicGroup, topic_prerequisites
from app.schemas.topics import slugify

Library = list[tuple[str, list[tuple[str, list[str]]]]]

TOPIC_LIBRARY: Library = [
    (
        "OOP Fundamentals",
        [
            (
                "Programming Paradigms and Objects",
                [
                    "Procedural vs Object-Oriented Programming",
                    "Classes and Objects",
                    "Attributes and Methods",
                    "Object State and Behavior",
                    "Object Identity",
                ],
            ),
            (
                "Access Control and Members",
                [
                    "Encapsulation Fundamentals",
                    "Access Modifiers",
                    "Public, Private and Protected",
                    "Static and Instance Members",
                    "this and super",
                ],
            ),
            (
                "Constructors and Object Lifecycle",
                [
                    "Constructors",
                    "Constructor Overloading",
                    "Default Constructors",
                    "Parameterized Constructors",
                    "Object Initialization",
                    "Object Lifecycle",
                ],
            ),
        ],
    ),
    (
        "Four Pillars of OOP",
        [
            ("Encapsulation", ["Encapsulation"]),
            (
                "Inheritance",
                ["Inheritance", "Single Inheritance", "Multilevel Inheritance", "Hierarchical Inheritance"],
            ),
            (
                "Polymorphism",
                [
                    "Method Overloading",
                    "Method Overriding",
                    "Compile-time Polymorphism",
                    "Runtime Polymorphism",
                    "Dynamic Method Dispatch",
                ],
            ),
            ("Abstraction", ["Abstraction", "Abstract Classes", "Interfaces", "Abstract Class vs Interface"]),
        ],
    ),
    (
        "Advanced OOP Concepts",
        [
            (
                "Object Relationships",
                ["Association", "Aggregation", "Composition", "Dependency", "Delegation", "Object Relationships"],
            ),
            ("Coupling and Cohesion", ["Coupling", "Cohesion"]),
            ("Nested and Final Types", ["Inner Classes", "Anonymous Classes", "Final Classes", "Final Methods"]),
            ("Casting and Binding", ["Upcasting", "Downcasting", "Object Casting", "Early Binding", "Late Binding"]),
        ],
    ),
    (
        "Java Language and OOP Features",
        [
            (
                "Types and Values",
                ["Primitive and Reference Types", "Wrapper Classes", "Pass by Value", "String and StringBuilder"],
            ),
            ("The Object Class", ["Object Class", "equals()", "hashCode()", "toString()"]),
            ("Exceptions", ["Exception Handling", "Checked and Unchecked Exceptions", "Custom Exceptions"]),
            (
                "Packages, Generics and Collections",
                ["Packages and Imports", "Generics", "Collections Framework", "Lambda Expressions"],
            ),
        ],
    ),
    (
        "SOLID Principles",
        [
            (
                "The Five Principles",
                [
                    "Single Responsibility Principle",
                    "Open/Closed Principle",
                    "Liskov Substitution Principle",
                    "Interface Segregation Principle",
                    "Dependency Inversion Principle",
                ],
            ),
            (
                "Applying SOLID",
                ["Applying SOLID Together", "Identifying SOLID Violations", "Refactoring SOLID Violations"],
            ),
        ],
    ),
    (
        "Clean Code",
        [
            (
                "Clean Code Foundations",
                ["Meaning of Clean Code", "Readability", "Code Formatting", "Comments and Documentation"],
            ),
            (
                "Naming and Functions",
                [
                    "Meaningful Naming",
                    "Functions and Methods",
                    "Small Functions",
                    "Single Responsibility of Functions",
                ],
            ),
            (
                "Simplifying Logic",
                ["Avoiding Magic Numbers", "Constants", "Error Handling", "Avoiding Deep Nesting", "Guard Clauses"],
            ),
            (
                "Clean Code Principles",
                [
                    "Code Duplication",
                    "DRY Principle",
                    "KISS Principle",
                    "YAGNI Principle",
                    "Boy Scout Rule",
                    "Clean Code Refactoring",
                ],
            ),
        ],
    ),
    (
        "Code Smells",
        [
            ("Bloaters", ["Long Method", "Large Class", "God Class", "Primitive Obsession", "Data Clumps"]),
            (
                "Object-Orientation Abusers",
                [
                    "Switch Statements",
                    "Temporary Field",
                    "Refused Bequest",
                    "Alternative Classes with Different Interfaces",
                ],
            ),
            ("Change Preventers", ["Divergent Change", "Shotgun Surgery", "Parallel Inheritance Hierarchies"]),
            ("Dispensables", ["Duplicate Code", "Lazy Class", "Dead Code", "Speculative Generality"]),
            ("Couplers", ["Feature Envy", "Inappropriate Intimacy", "Message Chains", "Middle Man"]),
        ],
    ),
    (
        "Refactoring Techniques",
        [
            ("Composing Methods", ["Extract Method", "Inline Method", "Rename Method"]),
            ("Moving Features Between Objects", ["Extract Class", "Inline Class", "Move Method", "Move Field"]),
            (
                "Organizing Data",
                ["Encapsulate Field", "Replace Magic Number with Constant", "Replace Type Code with Subclasses"],
            ),
            (
                "Simplifying Conditionals and Calls",
                ["Replace Conditional with Polymorphism", "Introduce Parameter Object", "Preserve Whole Object"],
            ),
            (
                "Dealing with Generalization",
                ["Pull Up Method", "Push Down Method", "Replace Inheritance with Delegation"],
            ),
        ],
    ),
    (
        "Design Patterns",
        [
            ("Creational", ["Singleton", "Factory Method", "Abstract Factory", "Builder", "Prototype"]),
            ("Structural", ["Adapter", "Decorator", "Facade", "Proxy", "Composite", "Bridge"]),
            (
                "Behavioral",
                [
                    "Strategy",
                    "Observer",
                    "Command",
                    "State",
                    "Template Method",
                    "Iterator",
                    "Mediator",
                    "Chain of Responsibility",
                ],
            ),
        ],
    ),
    (
        "Software Design Principles",
        [
            ("Modularity", ["High Cohesion", "Low Coupling", "Separation of Concerns", "Information Hiding"]),
            (
                "Designing with Abstractions",
                [
                    "Programming to an Interface",
                    "Composition over Inheritance",
                    "Dependency Injection",
                    "Encapsulation of Change",
                ],
            ),
            ("Object Collaboration", ["Law of Demeter", "Tell Don't Ask"]),
        ],
    ),
    (
        "UML and Software Modeling",
        [
            (
                "UML Diagrams",
                ["Class Diagrams", "Use Case Diagrams", "Sequence Diagrams", "Activity Diagrams", "Object Diagrams"],
            ),
            (
                "Class Diagram Relationships",
                [
                    "Inheritance Relationships",
                    "Association Multiplicity",
                    "Aggregation Notation",
                    "Composition Notation",
                    "Interface Representation",
                    "UML Relationships",
                ],
            ),
        ],
    ),
    (
        "Testing and Maintainability",
        [
            (
                "Testing Levels and Practices",
                ["Unit Testing", "Integration Testing", "Test-Driven Development", "Regression Testing"],
            ),
            ("Writing Tests with JUnit", ["JUnit Basics", "Assertions", "Test Cases", "Edge Cases"]),
            ("Test Doubles and Coverage", ["Mocking", "Stubbing", "Code Coverage"]),
            ("Maintainability", ["Maintainability", "Testability", "Technical Debt"]),
        ],
    ),
]

# (topic, prerequisite) pairs, by topic name.
PREREQUISITES: list[tuple[str, str]] = [
    ("Classes and Objects", "Procedural vs Object-Oriented Programming"),
    ("Constructor Overloading", "Constructors"),
    ("Constructor Overloading", "Method Overloading"),
    ("Encapsulation", "Access Modifiers"),
    ("Single Inheritance", "Inheritance"),
    ("Multilevel Inheritance", "Single Inheritance"),
    ("Hierarchical Inheritance", "Single Inheritance"),
    ("Method Overriding", "Inheritance"),
    ("Runtime Polymorphism", "Method Overriding"),
    ("Compile-time Polymorphism", "Method Overloading"),
    ("Dynamic Method Dispatch", "Runtime Polymorphism"),
    ("Abstract Class vs Interface", "Abstract Classes"),
    ("Abstract Class vs Interface", "Interfaces"),
    ("Downcasting", "Upcasting"),
    ("Late Binding", "Early Binding"),
    ("Composition", "Association"),
    ("Aggregation", "Association"),
    ("Liskov Substitution Principle", "Inheritance"),
    ("Dependency Inversion Principle", "Interfaces"),
    ("Identifying SOLID Violations", "Applying SOLID Together"),
    ("Refactoring SOLID Violations", "Identifying SOLID Violations"),
    ("Replace Conditional with Polymorphism", "Runtime Polymorphism"),
    ("Replace Conditional with Polymorphism", "Switch Statements"),
    ("Extract Method", "Long Method"),
    ("Extract Class", "Large Class"),
    ("Strategy", "Interfaces"),
    ("Decorator", "Composition"),
    ("Template Method", "Abstract Classes"),
    ("Composition over Inheritance", "Composition"),
    ("Mocking", "Unit Testing"),
    ("Stubbing", "Unit Testing"),
]


@dataclass
class SeedCounts:
    categories_created: int = 0
    groups_created: int = 0
    topics_created: int = 0
    prerequisites_created: int = 0


def seed_topic_library(db: Session, library: Library = TOPIC_LIBRARY) -> SeedCounts:
    """Insert any missing categories, chapters, topics and prerequisites.

    Idempotent: existing rows (matched by slug) are left untouched so administrator edits survive.
    """
    counts = SeedCounts()
    topics_by_name: dict[str, Topic] = {}

    for c_index, (category_name, groups) in enumerate(library):
        category = db.scalar(select(TopicCategory).where(TopicCategory.slug == slugify(category_name)))
        if category is None:
            category = TopicCategory(name=category_name, slug=slugify(category_name), sort_order=c_index)
            db.add(category)
            db.flush()
            counts.categories_created += 1

        for g_index, (group_name, topic_names) in enumerate(groups):
            group = db.scalar(
                select(TopicGroup).where(TopicGroup.category_id == category.id, TopicGroup.slug == slugify(group_name))
            )
            if group is None:
                group = TopicGroup(
                    category_id=category.id, name=group_name, slug=slugify(group_name), sort_order=g_index
                )
                db.add(group)
                db.flush()
                counts.groups_created += 1

            for t_index, topic_name in enumerate(topic_names):
                topic = db.scalar(select(Topic).where(Topic.slug == slugify(topic_name)))
                if topic is None:
                    topic = Topic(group_id=group.id, name=topic_name, slug=slugify(topic_name), sort_order=t_index)
                    db.add(topic)
                    db.flush()
                    counts.topics_created += 1
                topics_by_name[topic_name] = topic

    existing = set(db.execute(select(topic_prerequisites.c.topic_id, topic_prerequisites.c.prerequisite_id)))
    for topic_name, prerequisite_name in PREREQUISITES:
        topic, prerequisite = topics_by_name.get(topic_name), topics_by_name.get(prerequisite_name)
        if topic is None or prerequisite is None or (topic.id, prerequisite.id) in existing:
            continue
        db.execute(topic_prerequisites.insert().values(topic_id=topic.id, prerequisite_id=prerequisite.id))
        existing.add((topic.id, prerequisite.id))
        counts.prerequisites_created += 1

    db.commit()
    return counts

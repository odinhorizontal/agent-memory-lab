"""Seeded synthetic benchmark with independently assigned evidence labels."""

from dataclasses import asdict, dataclass
from datetime import UTC, datetime, timedelta
import json
import random

from ..models import BenchmarkCase, Candidate, MemoryType

DEFAULT_SEED = 42
DEFAULT_SIZE = 200
MAX_SIZE = 1000
JAN = datetime(2025, 1, 1, tzinfo=UTC)
MAR = datetime(2025, 3, 1, tzinfo=UTC)
JUN = datetime(2025, 6, 1, tzinfo=UTC)
OCT = datetime(2025, 10, 1, tzinfo=UTC)


@dataclass(frozen=True, slots=True)
class Fact:
    id: str
    candidate: Candidate
    recorded_at: datetime


@dataclass(frozen=True, slots=True)
class Dataset:
    seed: int
    facts: tuple[Fact, ...]
    cases: tuple[BenchmarkCase, ...]
    stale_after: dict[str, datetime]

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2,
                          default=datetime.isoformat) + "\n"


def generate_dataset(size: int = DEFAULT_SIZE, seed: int = DEFAULT_SEED) -> Dataset:
    rng = random.Random(seed)
    facts: list[Fact] = []
    cases: list[BenchmarkCase] = []
    stale_after: dict[str, datetime] = {}
    names = ["Aster", "Beryl", "Cedar", "Dahlia", "Elm", "Flint", "Garnet", "Hazel",
             "Iris", "Juniper", "Kite", "Laurel", "Maple", "Nettle", "Opal", "Pine",
             "Quartz", "Rowan", "Sage", "Thyme", "Umber", "Violet", "Willow", "Yew"]
    rng.shuffle(names)

    def fact(content: str, *, start: datetime = JAN, **fields) -> str:
        evidence = f"memory-{len(facts) + 1:04d}"
        recorded_at = start + timedelta(minutes=len(facts) + 1)
        candidate = Candidate(content, fields.pop("memory_type", MemoryType.SEMANTIC),
                              valid_from=start, **fields)
        facts.append(Fact(evidence, candidate, recorded_at))
        return evidence

    def case(query: str, category: str, *evidence: str, as_of=OCT, answer=None) -> None:
        cases.append(BenchmarkCase(f"query-{len(cases) + 1:03d}", query, category,
                                   evidence, as_of, answer))

    for name, material in zip(names[:10],
                              ["copper", "titanium", "glass", "steel", "quartz",
                               "carbon fiber", "brass", "linen", "ceramic", "aluminum"]):
        evidence = fact(f"The {name} enclosure material is {material}.")
        case(f"What enclosure material was selected for {name}?", "Exact Fact",
             evidence, answer=material)

    paraphrases = [
        ("The incident runbook requires a second reviewer for {n}.",
         "Who must double-check before {n} responds to an outage?"),
        ("{n} refrigerates samples immediately after collection.",
         "How does {n} keep specimens cold once taken?"),
        ("{n} maintains a fortnightly inspection schedule.",
         "How often does {n} arrange equipment checks?"),
        ("The {n} connector supports automatic failover.",
         "Can {n} switch paths without operator intervention?"),
        ("{n} prohibits storing plaintext credentials.",
         "Can {n} keep secrets unencrypted?"),
        ("{n} staggers its nightly snapshots across regions.",
         "How does {n} avoid simultaneous backups in every location?"),
        ("{n} stores its spare probes in the sealed cabinet.",
         "Where should {n} look for replacement sensors?"),
        ("{n} publishes all measurements using metric units.",
         "Which measurement system appears in {n} reports?"),
    ]
    for name, (statement, question) in zip(names[10:18], paraphrases):
        evidence = fact(statement.format(n=name))
        case(question.format(n=name), "Semantic Paraphrase", evidence)

    for name in names[18:]:
        initial, current = rng.sample(["SQLite", "PostgreSQL", "MariaDB", "DuckDB"], 2)
        slot = {"entity": name, "attribute": "database"}
        old = fact(f"{name} initially uses {initial} as its database.", value=initial, **slot)
        new = fact(f"{name} database migrated to {current}.", start=JUN, value=current,
                   replaces=True, previous_value=initial, **slot)
        stale_after[old] = JUN
        case(f"Which database was {name} using in March 2025?", "Temporal Update",
             old, as_of=MAR, answer=initial)
        case(f"Which database is {name} using in October 2025?", "Temporal Update",
             new, answer=current)

    for name in ["North Pier", "East Pier", "West Pier", "South Pier",
                 "Hill Depot", "Cove Depot", "River Depot", "Lake Depot"]:
        slot = {"entity": name, "attribute": "inspection-date"}
        proposed, reported = rng.sample(["Monday", "Tuesday", "Thursday", "Friday"], 2)
        first = fact(f"{name} inspection scheduled {proposed} according to the crew.",
                     value=proposed, **slot)
        second = fact(f"{name} inspection reported {reported} by operations.",
                      value=reported, **slot)
        case(f"What conflicting inspection dates were reported for {name}?",
             "Conflict", first, second)

    for site, team in zip(["Beacon", "Harbor", "Summit", "Delta", "Ridge", "Dune"],
                          ["Orchid", "Cypress", "Frond", "Lotus", "Spruce", "Moss"]):
        sensor = rng.choice(["barometer", "thermistor", "hygrometer"])
        link = fact(f"The {site} station is serviced by Team {team}.")
        tool = fact(f"Team {team} maintains the {sensor} and signs the calibration log.")
        case(f"Who services {site} station and what do they calibrate?",
             "Multi-hop", link, tool, answer=f"Team {team}, {sensor}")

    for question in [
        "What is the access code for the Beacon station?",
        "Which database stores the Comet observatory readings?",
        "What is the insurance renewal date for Cove Depot?",
        "When did Team Lotus decommission its satellite?",
        "Who designed the Aster enclosure prototype?",
        "What did the Juniper procurement package cost?",
    ]:
        case(question, "Unanswerable")

    if not len(facts) <= size <= MAX_SIZE:
        raise ValueError(f"Memory size must be in [{len(facts)}, {MAX_SIZE}]")
    distractors = [
        "Station {label} archived a calibration log for its enclosure.",
        "Team {label} tested a backup database for weather observations.",
        "Depot {label} scheduled a quarterly inspection of spare sensors.",
        "Project {label} measured maintenance costs for paper records.",
        "Warehouse {label} photographed the storage cabinet after a checklist review.",
    ]
    while len(facts) < size:
        label = f"{rng.choice(names)} Annex {len(facts) + 1}"
        fact(rng.choice(distractors).format(label=label),
             start=JAN + timedelta(days=rng.randrange(1, 255)),
             memory_type=rng.choice(list(MemoryType)))

    facts.sort(key=lambda item: (item.recorded_at, item.id))
    rng.shuffle(cases)
    return Dataset(seed, tuple(facts), tuple(cases), stale_after)

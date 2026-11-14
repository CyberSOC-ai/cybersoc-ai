"""Interactive incident selection and inspection over the shared No-RAG runner."""

import json
from pathlib import Path
import re
from uuid import uuid4

from . import run as shared
from ai.runtime.contracts import contract_validators


def display(value):
    """Do not interpret terminal control sequences from incident/model text."""
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False)
    print(re.sub(r"[\x00-\x08\x0b-\x1f\x7f-\x9f]",
                 lambda match: f"\\u{ord(match.group()):04x}", text))


def inspect(folder, name):
    path = folder / name
    if path.exists():
        display(shared.strict_json(path.read_text(encoding="utf-8")))
    else:
        print(f"No {name} saved for this attempt.")


def show_result(folder):
    path = folder / "result.json"
    if not path.exists():
        inspect(folder, "failure.json")
        return
    result = shared.strict_json(path.read_text(encoding="utf-8"))
    print("\nAssessment (contract-valid; review correctness):")
    display(result["summary"])
    display(f"Verdict: {result['triage_verdict']} | Risk: {result['risk_level']}")
    display({"mitre_techniques": result["mitre_techniques"],
             "recommended_actions": result["recommended_actions"]})
    print("Proposals only; nothing executed.")


def session(config, release, output):
    inputs, _ = shared.release_inputs(release, contract_validators(shared.ROOT))
    print("CyberSOC AI — shared-dev-v1 No-RAG terminal")
    print("Choose an incident to view its observations. Run analysis when ready.")
    print("Each analysis starts a separate run; the model does not retain earlier cases.")
    try:
        while True:
            print("\nShared incidents:")
            for number, incident in enumerate(inputs, 1):
                display(f"  {number}. {incident['incident_id']}")
            choice = input("Incident number, or q to quit: ").strip().lower()
            if choice == "q":
                return 0
            if choice not in {str(i) for i in range(1, len(inputs) + 1)}:
                print("Choose one of the listed numbers.")
                continue
            incident = inputs[int(choice) - 1]
            iid, last = incident["incident_id"], None
            print("\nIncident observations:")
            display(incident)
            while True:
                command = input("\n[r] Run analysis  [i] Input  [j] Raw answer  [t] Trace  [b] Back  [q] Quit: ").strip().lower()
                if command == "q":
                    return 0
                if command == "b":
                    break
                if command == "i":
                    display(incident)
                elif command in ("j", "t"):
                    if last is None:
                        print("Run analysis first.")
                    else:
                        inspect(last / iid, "raw-output.json" if command == "j" else "trace.json")
                elif command == "r":
                    last = Path(output) / ("attempt-" + uuid4().hex)
                    display(f"Starting local model. Saving to: {last}")
                    try:
                        shared.run(config, release, last, case=iid)
                    except KeyboardInterrupt:
                        print("Analysis interrupted; available evidence retained.")
                        return 130
                    except Exception as exc:
                        print(f"Analysis stopped: {type(exc).__name__}. Check configuration and runtime.log.")
                    if (last / "report.json").exists():
                        report = shared.strict_json((last / "report.json").read_text(encoding="utf-8"))
                        display(f"Run status: {report['status']}")
                        show_result(last / iid)
                else:
                    print("Choose r, i, j, t, b or q.")
    except (EOFError, KeyboardInterrupt):
        print("\nTerminal closed.")
        return 0

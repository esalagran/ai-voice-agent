from __future__ import annotations

import argparse

from ehr_service.api import create_app
from ehr_service.database import database_url, init_db, make_session_factory
from ehr_service.seed import seed_demo_data

app = create_app()


def main() -> None:
    parser = argparse.ArgumentParser(description="Run or seed the local EHR service.")
    parser.add_argument("--seed", action="store_true", help="Insert deterministic demo data")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=7861, type=int)
    args = parser.parse_args()

    session_factory = make_session_factory(database_url())
    init_db(session_factory)

    if args.seed:
        seed_demo_data(session_factory)
        print("Seeded local EHR demo data.")
        return

    import uvicorn

    uvicorn.run("ehr:app", host=args.host, port=args.port)


if __name__ == "__main__":
    main()

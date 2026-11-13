"""
Seeds a Google Cloud Healthcare FHIR R4 Store with the unified 7-patient
Emergency Ward + Longitudinal EHR Chart (`ehr_chart_summary_agent`) cohort (`pat-001` through `pat-007`).

Reads `GOOGLE_CLOUD_PROJECT`, `FHIR_DATASET_LOCATION`, `FHIR_DATASET_ID`, and `FHIR_STORE_ID`
from `.env` (or CLI flags `--project`, `--location`, `--dataset`, `--fhir-store`).
"""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
import google.auth
from dotenv import load_dotenv
from google.auth.transport import requests as grequests

try:
    from .fhir_cohort_data import get_emergency_ward_resources
except ImportError:
    from fhir_cohort_data import get_emergency_ward_resources  # type: ignore

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

load_dotenv(Path(__file__).resolve().parent / ".env", override=True)

BASE_URL = "https://healthcare.googleapis.com/v1"


def get_authorized_session() -> grequests.AuthorizedSession:
    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    return grequests.AuthorizedSession(creds)


def ensure_dataset_and_fhir_store(
    session: grequests.AuthorizedSession,
    project_id: str,
    location: str,
    dataset_id: str,
    fhir_store_id: str,
) -> str:
    parent = f"{BASE_URL}/projects/{project_id}/locations/{location}"
    dataset_url = f"{parent}/datasets/{dataset_id}"

    r_ds = session.get(dataset_url, timeout=15)
    if r_ds.status_code == 404:
        logging.info("Creating Healthcare Dataset '%s' in %s/%s...", dataset_id, project_id, location)
        r_create_ds = session.post(
            f"{parent}/datasets",
            params={"datasetId": dataset_id},
            json={},
            timeout=15,
        )
        if r_create_ds.status_code not in (200, 201, 409):
            r_create_ds.raise_for_status()
        for _ in range(45):
            if session.get(dataset_url, timeout=10).status_code == 200:
                break
            time.sleep(4)
    else:
        r_ds.raise_for_status()
        logging.info("Healthcare Dataset '%s' verified.", dataset_id)

    fhir_store_url = f"{dataset_url}/fhirStores/{fhir_store_id}"
    r_fs = session.get(fhir_store_url, timeout=15)
    if r_fs.status_code in (404, 403):
        logging.info("Creating FHIR R4 Store '%s'...", fhir_store_id)
        r_create_fs = session.post(
            f"{dataset_url}/fhirStores",
            params={"fhirStoreId": fhir_store_id},
            json={
                "version": "R4",
                "enableUpdateCreate": True,
                "disableReferentialIntegrity": False,
            },
            timeout=15,
        )
        if r_create_fs.status_code not in (200, 201, 409):
            r_create_fs.raise_for_status()
        time.sleep(2)
    else:
        r_fs.raise_for_status()
        logging.info("FHIR Store '%s' verified.", fhir_store_id)

    return f"{fhir_store_url}/fhir"


def seed_all(
    project_id: str,
    location: str,
    dataset_id: str,
    fhir_store_id: str,
) -> None:
    session = get_authorized_session()
    fhir_base = ensure_dataset_and_fhir_store(
        session=session,
        project_id=project_id,
        location=location,
        dataset_id=dataset_id,
        fhir_store_id=fhir_store_id,
    )
    headers = {"Content-Type": "application/fhir+json;charset=utf-8"}

    resources = get_emergency_ward_resources()
    ok_count = 0
    err_count = 0
    for rtype, rid, body in resources:
        url = f"{fhir_base}/{rtype}/{rid}"
        resp = session.put(url, headers=headers, json=body, timeout=15)
        if resp.status_code in (200, 201):
            ok_count += 1
        else:
            err_count += 1
            logging.error("Failed %s/%s (HTTP %d): %s", rtype, rid, resp.status_code, resp.text)

    logging.info(
        "Completed FHIR R4 seeding in projects/%s/locations/%s/datasets/%s/fhirStores/%s: %d succeeded, %d failed.",
        project_id,
        location,
        dataset_id,
        fhir_store_id,
        ok_count,
        err_count,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed GCP Cloud Healthcare FHIR R4 Store with pat-001..pat-007")
    parser.add_argument("--project", default=os.getenv("GOOGLE_CLOUD_PROJECT", "gsd-argolis-playground"))
    parser.add_argument("--location", default=os.getenv("FHIR_DATASET_LOCATION", "asia-east1"))
    parser.add_argument("--dataset", default=os.getenv("FHIR_DATASET_ID", "test"))
    parser.add_argument("--fhir-store", default=os.getenv("FHIR_STORE_ID", "synthe_data"))
    args = parser.parse_args()

    seed_all(
        project_id=args.project,
        location=args.location,
        dataset_id=args.dataset,
        fhir_store_id=args.fhir_store,
    )


if __name__ == "__main__":
    main()

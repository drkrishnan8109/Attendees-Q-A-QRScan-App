"""Presenter backup download and restore controls."""

from __future__ import annotations

import streamlit as st

from qa_app.models import Room
from qa_app.storage import BackupConflictError, BackupFormatError, QADatabase


def render_backups(database: QADatabase, rooms: list[Room]) -> None:
    """Render safe exports and an empty-database-only restore workflow."""

    st.header("Backups")
    st.warning(
        "Community Cloud can delete local SQLite data during a restart or redeploy. "
        "Download a JSON backup after each presentation."
    )
    downloads = st.columns(2)
    with downloads[0]:
        st.download_button(
            "Download restorable JSON",
            data=database.export_backup_json(),
            file_name="live-qa-backup.json",
            mime="application/json",
            key="download_json",
            width="stretch",
        )
    with downloads[1]:
        st.download_button(
            "Download readable CSV",
            data=database.export_questions_csv(),
            file_name="live-qa-questions.csv",
            mime="text/csv",
            key="download_csv",
            width="stretch",
        )

    st.subheader("Restore a JSON backup")
    if rooms:
        st.info(
            "Restore becomes available when this app database is empty. This prevents "
            "an upload from silently merging with or replacing current questions."
        )
    uploaded_backup = st.file_uploader(
        "Backup file",
        type=["json"],
        key="backup_upload",
        disabled=bool(rooms),
        help="Maximum accepted backup size: 1 MB.",
    )
    restore_clicked = st.button(
        "Restore backup",
        key="restore_backup",
        disabled=bool(rooms),
    )
    if restore_clicked and uploaded_backup is None:
        st.error("Choose a JSON backup first.")
    if restore_clicked and uploaded_backup is not None:
        try:
            summary = database.restore_backup_json(uploaded_backup.getvalue())
        except (BackupConflictError, BackupFormatError) as error:
            st.error(str(error))
        else:
            st.success(
                f"Restored {summary.rooms} rooms, {summary.questions} questions, "
                f"and {summary.reactions} reactions."
            )
            st.rerun()

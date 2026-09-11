from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Barrier
from uuid import uuid4

import pytest
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.api.routes_auth import delete_account
from app.auth.schemas import AccountDeleteRequest
from app.auth.service import create_user, user_context
from app.db.session import create_database_engine
from app.models.analysis_request import AnalysisRequestModel
from app.models.report import ReportModel
from app.models.organization import OrganizationMembershipModel, OrganizationModel
from app.models.research_intelligence import ResearchReportComparisonModel, ThesisAssumptionModel, ThesisCatalystModel, ThesisRevisionModel
from app.models.saved_thesis import SavedThesisModel
from app.models.user import UserModel
from app.research_intelligence.schemas import (
    CatalystCreateRequest,
    CatalystUpdateRequest,
    ReportComparisonRequest,
    ResearchAssumptionCreateRequest,
    ResearchAssumptionUpdateRequest,
    ThesisStatusUpdateRequest,
)
from app.research_intelligence.service import (
    append_material_revision,
    compare_reports,
    create_catalyst,
    create_assumption,
    create_initial_revision,
    list_history,
    update_catalyst,
    update_assumption,
    update_status,
)
from app.organizations.service import delete_organization
from app.schemas.reports import ReportResponse, ReportSection, SourceReference
from app.theses.schemas import ThesisUpdateRequest
from app.theses.service import get_thesis, update_thesis


pytestmark = pytest.mark.postgres_integration


@pytest.fixture(scope="module")
def postgres_sessions() -> sessionmaker:
    if os.getenv("RUN_POSTGRES_INTEGRATION") != "true":
        pytest.skip("Phase 21D PostgreSQL tests require RUN_POSTGRES_INTEGRATION=true")
    engine = create_database_engine()
    if engine.dialect.name != "postgresql":
        pytest.skip("Phase 21D PostgreSQL tests require a PostgreSQL DATABASE_URL")
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)


def test_postgres_thesis_revision_and_assumption_heads_serialise_without_lost_updates(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-concurrency-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_pg_{suffix}",
            owner_user_id=user.id,
            title="PostgreSQL research thesis",
            strategy_text="Concurrent revision authority must be database serialized.",
            protocols=["pendle"],
            assumptions_json={"legacy": "unchanged"},
            visibility="private",
        )
        db.add(thesis)
        create_initial_revision(db, thesis, user.id)
        db.commit()
        user_id, thesis_id = user.id, thesis.id

    revision_barrier = Barrier(2)

    def append_revision() -> int:
        with postgres_sessions() as db:
            revision_barrier.wait(timeout=10)
            thesis = db.execute(
                select(SavedThesisModel).where(SavedThesisModel.id == thesis_id).with_for_update()
            ).scalars().one()
            record = append_material_revision(
                db,
                thesis,
                actor_user_id=user_id,
                change_reason="Concurrent revision test",
            )
            db.commit()
            return record.revision_number

    with ThreadPoolExecutor(max_workers=2) as executor:
        numbers = list(executor.map(lambda _value: append_revision(), range(2)))
    assert sorted(numbers) == [2, 3]

    with postgres_sessions() as db:
        actor = user_context(db.get(UserModel, user_id))
        created = create_assumption(
            db,
            actor,
            thesis_id,
            ResearchAssumptionCreateRequest(
                statement="The documented maturity remains applicable.",
                expected_thesis_revision=3,
            ),
        )
        assumption_id = created.id

    assumption_barrier = Barrier(2)

    def revise_assumption() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            assumption_barrier.wait(timeout=10)
            try:
                update_assumption(
                    db,
                    actor,
                    thesis_id,
                    assumption_id,
                    ResearchAssumptionUpdateRequest(
                        statement="The maturity evidence was reviewed.",
                        state="weakened",
                        expected_revision=1,
                        expected_thesis_revision=4,
                    ),
                )
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda _value: revise_assumption(), range(2)))
    assert sorted(outcomes) == [200, 409]
    with postgres_sessions() as db:
        versions = db.scalars(
            select(ThesisAssumptionModel)
            .where(ThesisAssumptionModel.thesis_id == thesis_id)
            .where(ThesisAssumptionModel.assumption_id == assumption_id)
            .order_by(ThesisAssumptionModel.revision_number)
        ).all()
        assert [item.revision_number for item in versions] == [1, 2]
        assert len(db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == thesis_id)).all()) >= 5


def test_postgres_legacy_baseline_initialization_is_idempotent_under_concurrent_reads(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-baseline-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_baseline_{suffix}",
            owner_user_id=user.id,
            title="Legacy baseline thesis",
            strategy_text="The saved content must remain unchanged while history starts.",
            protocols=["pendle"],
            assumptions_json={"legacy": "exact"},
            visibility="private",
        )
        db.add(thesis)
        db.commit()
        user_id, thesis_id = user.id, thesis.id
    barrier = Barrier(2)

    def read_history() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            return len(list_history(db, actor, thesis_id).items)

    with ThreadPoolExecutor(max_workers=2) as executor:
        assert list(executor.map(lambda _value: read_history(), range(2))) == [1, 1]
    with postgres_sessions() as db:
        rows = db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == thesis_id)).all()
        assert len(rows) == 1
        assert rows[0].origin == "legacy_baseline"


def test_postgres_first_legacy_mutation_and_history_read_preserve_the_original_baseline(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-first-mutation-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_first_mutation_{suffix}",
            owner_user_id=user.id,
            title="Original PostgreSQL legacy thesis",
            strategy_text="The original row must survive concurrent baseline initialization.",
            protocols=["pendle"],
            assumptions_json={"legacy": "original"},
            visibility="private",
        )
        db.add(thesis)
        db.commit()
        user_id, thesis_id = user.id, thesis.id
    barrier = Barrier(2)

    def mutate() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            update_thesis(
                db,
                actor,
                thesis_id,
                ThesisUpdateRequest(title="Updated PostgreSQL legacy thesis", expected_revision=1),
            )
            return 200

    def read() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            return len(list_history(db, actor, thesis_id).items)

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda action: action(), (mutate, read)))
    assert outcomes[0] == 200
    assert outcomes[1] in {1, 2}
    with postgres_sessions() as db:
        rows = db.scalars(
            select(ThesisRevisionModel)
            .where(ThesisRevisionModel.thesis_id == thesis_id)
            .order_by(ThesisRevisionModel.revision_number)
        ).all()
        assert [(row.revision_number, row.title, row.assumptions_snapshot) for row in rows] == [
            (1, "Original PostgreSQL legacy thesis", {"legacy": "original"}),
            (2, "Updated PostgreSQL legacy thesis", {"legacy": "original"}),
        ]


def test_postgres_status_and_thesis_update_race_has_one_winner_and_monotonic_history(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-state-race-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_state_race_{suffix}",
            owner_user_id=user.id,
            title="Original state race thesis",
            strategy_text="The thesis row is the PostgreSQL serialization authority.",
            protocols=["pendle"],
            assumptions_json={},
            visibility="private",
        )
        db.add(thesis)
        create_initial_revision(db, thesis, user.id)
        db.commit()
        user_id, thesis_id = user.id, thesis.id
    barrier = Barrier(2)

    def change_status() -> tuple[str, int]:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            try:
                update_status(db, actor, thesis_id, ThesisStatusUpdateRequest(status="challenged", expected_revision=1))
                return "status", 200
            except HTTPException as exc:
                db.rollback()
                return "status", exc.status_code

    def change_title() -> tuple[str, int]:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            try:
                update_thesis(db, actor, thesis_id, ThesisUpdateRequest(title="Updated state race thesis", expected_revision=1))
                return "title", 200
            except HTTPException as exc:
                db.rollback()
                return "title", exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = dict(executor.map(lambda action: action(), (change_status, change_title)))
    assert sorted(outcomes.values()) == [200, 409]
    with postgres_sessions() as db:
        thesis = db.get(SavedThesisModel, thesis_id)
        rows = db.scalars(
            select(ThesisRevisionModel)
            .where(ThesisRevisionModel.thesis_id == thesis_id)
            .order_by(ThesisRevisionModel.revision_number)
        ).all()
        assert [row.revision_number for row in rows] == [1, 2]
        if outcomes["status"] == 200:
            assert rows[-1].status == "challenged"
            assert thesis.title == "Original state race thesis"
        else:
            assert rows[-1].status == "draft"
            assert thesis.title == "Updated state race thesis"


def test_postgres_catalyst_updates_with_same_revision_have_one_winner(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-catalyst-race-{suffix}@example.test")
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_catalyst_race_{suffix}",
            owner_user_id=user.id,
            title="Catalyst race thesis",
            strategy_text="Catalyst updates use the thesis lock and catalyst revision authority.",
            protocols=["pendle"],
            assumptions_json={},
            visibility="private",
        )
        db.add(thesis)
        create_initial_revision(db, thesis, user.id)
        db.commit()
        actor = user_context(user)
        catalyst = create_catalyst(
            db,
            actor,
            thesis.id,
            CatalystCreateRequest(title="Original catalyst", date_precision="unknown", expected_thesis_revision=1),
        )
        user_id, thesis_id, catalyst_id = user.id, thesis.id, catalyst.id
    barrier = Barrier(2)

    def update(title: str) -> tuple[str, int]:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            try:
                update_catalyst(
                    db,
                    actor,
                    thesis_id,
                    catalyst_id,
                    CatalystUpdateRequest(
                        title=title,
                        date_precision="unknown",
                        expected_revision=1,
                        expected_thesis_revision=2,
                    ),
                )
                return title, 200
            except HTTPException as exc:
                db.rollback()
                return title, exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = dict(executor.map(update, ("Catalyst update A", "Catalyst update B")))
    assert sorted(outcomes.values()) == [200, 409]
    winning_title = next(title for title, status in outcomes.items() if status == 200)
    with postgres_sessions() as db:
        catalyst = db.get(ThesisCatalystModel, catalyst_id)
        rows = db.scalars(
            select(ThesisRevisionModel)
            .where(ThesisRevisionModel.thesis_id == thesis_id)
            .order_by(ThesisRevisionModel.revision_number)
        ).all()
        assert catalyst.title == winning_title
        assert catalyst.revision_number == 2
        assert [row.revision_number for row in rows] == [1, 2, 3]


def test_postgres_report_comparison_unique_input_authority(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        user = create_user(db, f"phase21d-comparison-{suffix}@example.test")
        _persist_report(db, f"report_phase21d_pg_left_{suffix}", user.id, "Left deterministic strategy", "Moderate")
        _persist_report(db, f"report_phase21d_pg_right_{suffix}", user.id, "Right deterministic strategy", "Aggressive")
        db.commit()
        user_id = user.id
    left_id, right_id = f"report_phase21d_pg_left_{suffix}", f"report_phase21d_pg_right_{suffix}"
    barrier = Barrier(2)

    def compare() -> str:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, user_id))
            barrier.wait(timeout=10)
            return compare_reports(db, actor, ReportComparisonRequest(left_report_id=left_id, right_report_id=right_id)).id

    with ThreadPoolExecutor(max_workers=2) as executor:
        comparison_ids = list(executor.map(lambda _value: compare(), range(2)))
    assert len(set(comparison_ids)) == 1
    with postgres_sessions() as db:
        rows = db.scalars(
            select(ResearchReportComparisonModel)
            .where(ResearchReportComparisonModel.left_report_id == left_id)
            .where(ResearchReportComparisonModel.right_report_id == right_id)
        ).all()
        assert len(rows) == 1


def test_postgres_organization_saved_thesis_access_fails_closed_for_membership_and_lifecycle(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        owner = create_user(db, f"phase21d-org-owner-{suffix}@example.test")
        member = create_user(db, f"phase21d-org-member-{suffix}@example.test")
        org = OrganizationModel(
            id=f"org_phase21d_pg_{suffix}",
            name="Phase 21D PostgreSQL organization",
            slug=f"phase21d-pg-{suffix}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(org)
        db.flush()
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_org_pg_{suffix}",
            owner_user_id=owner.id,
            organization_id=org.id,
            title="Organization PostgreSQL thesis",
            strategy_text="Current organization authority must control saved thesis visibility.",
            protocols=["pendle"],
            assumptions_json={},
            visibility="organization",
        )
        db.add_all([
            OrganizationMembershipModel(
                id=f"membership_phase21d_pg_owner_{suffix}",
                organization_id=org.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            OrganizationMembershipModel(
                id=f"membership_phase21d_pg_member_{suffix}",
                organization_id=org.id,
                user_id=member.id,
                role="member",
                status="active",
            ),
            thesis,
        ])
        create_initial_revision(db, thesis, owner.id)
        db.commit()
        owner_id, member_id, organization_id, thesis_id = owner.id, member.id, org.id, thesis.id

    with postgres_sessions() as db:
        member_actor = user_context(db.get(UserModel, member_id))
        assert get_thesis(db, member_actor, thesis_id).id == thesis_id
        db.get(OrganizationModel, organization_id).status = "disabled"
        db.commit()
    with postgres_sessions() as db:
        with pytest.raises(HTTPException) as exc_info:
            get_thesis(db, user_context(db.get(UserModel, member_id)), thesis_id)
        assert exc_info.value.status_code == 404
        db.get(OrganizationModel, organization_id).status = "active"
        db.commit()
    with postgres_sessions() as db:
        membership = db.execute(
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == organization_id)
            .where(OrganizationMembershipModel.user_id == owner_id)
        ).scalars().one()
        membership.status = "removed"
        db.commit()
    with postgres_sessions() as db:
        owner_actor = user_context(db.get(UserModel, owner_id))
        with pytest.raises(HTTPException) as exc_info:
            update_thesis(db, owner_actor, thesis_id, ThesisUpdateRequest(title="Former creator write", expected_revision=1))
        assert exc_info.value.status_code == 404
        assert get_thesis(db, user_context(db.get(UserModel, member_id)), thesis_id).id == thesis_id
        db.get(OrganizationModel, organization_id).deleted_at = datetime.now(UTC)
        db.commit()
    with postgres_sessions() as db:
        with pytest.raises(HTTPException) as exc_info:
            get_thesis(db, user_context(db.get(UserModel, member_id)), thesis_id)
        assert exc_info.value.status_code == 404


def test_postgres_account_deletion_preserves_organization_research_for_remaining_owner(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        creator = create_user(db, f"phase21d-account-creator-{suffix}@example.test")
        remaining_owner = create_user(db, f"phase21d-account-owner-{suffix}@example.test")
        organization = OrganizationModel(
            id=f"org_phase21d_account_{suffix}",
            name="Phase 21D account lifecycle organization",
            slug=f"phase21d-account-{suffix}",
            status="active",
            created_by_user_id=creator.id,
        )
        organization_thesis = SavedThesisModel(
            id=f"thesis_phase21d_account_org_{suffix}",
            owner_user_id=creator.id,
            organization_id=organization.id,
            title="Organization account lifecycle thesis",
            strategy_text="Organization research must survive a former creator account deletion.",
            protocols=["pendle"],
            assumptions_json={},
            visibility="organization",
        )
        private_thesis = SavedThesisModel(
            id=f"thesis_phase21d_account_private_{suffix}",
            owner_user_id=creator.id,
            title="Private account lifecycle thesis",
            strategy_text="Private research must be disposed with the user account.",
            protocols=["pendle"],
            assumptions_json={},
            visibility="private",
        )
        db.add(organization)
        db.flush()
        db.add_all([
            OrganizationMembershipModel(
                id=f"membership_phase21d_account_creator_{suffix}",
                organization_id=organization.id,
                user_id=creator.id,
                role="owner",
                status="active",
            ),
            OrganizationMembershipModel(
                id=f"membership_phase21d_account_remaining_{suffix}",
                organization_id=organization.id,
                user_id=remaining_owner.id,
                role="member",
                status="active",
            ),
            organization_thesis,
            private_thesis,
        ])
        create_initial_revision(db, organization_thesis, creator.id)
        create_initial_revision(db, private_thesis, creator.id)
        db.commit()

        creator_actor = user_context(db.get(UserModel, creator.id))
        create_assumption(
            db,
            creator_actor,
            organization_thesis.id,
            ResearchAssumptionCreateRequest(
                statement="Organization evidence remains with the organization.",
                evidence_references=[{"unverified_reference": "organization-account-lifecycle-evidence"}],
                expected_thesis_revision=1,
            ),
        )
        create_catalyst(
            db,
            creator_actor,
            organization_thesis.id,
            CatalystCreateRequest(
                title="Organization catalyst",
                date_precision="unknown",
                expected_thesis_revision=2,
            ),
        )
        create_assumption(
            db,
            creator_actor,
            private_thesis.id,
            ResearchAssumptionCreateRequest(
                statement="Private evidence is removed with the user account.",
                expected_thesis_revision=1,
            ),
        )
        create_catalyst(
            db,
            creator_actor,
            private_thesis.id,
            CatalystCreateRequest(title="Private catalyst", date_precision="unknown", expected_thesis_revision=2),
        )
        comparison = ResearchReportComparisonModel(
            id=f"cmp_phase21d_account_{suffix}",
            left_report_id=f"report_phase21d_account_left_{suffix}",
            right_report_id=f"report_phase21d_account_right_{suffix}",
            left_input_checksum="a" * 64,
            right_input_checksum="b" * 64,
            scope_class="organization",
            scope_key=f"organization:{organization.id}",
            owner_user_id=creator.id,
            organization_id=organization.id,
            comparison_json={"deterministic": True},
            lineage_digest="c" * 64,
        )
        private_comparison = ResearchReportComparisonModel(
            id=f"cmp_phase21d_account_private_{suffix}",
            left_report_id=f"report_phase21d_account_private_left_{suffix}",
            right_report_id=f"report_phase21d_account_private_right_{suffix}",
            left_input_checksum="d" * 64,
            right_input_checksum="e" * 64,
            scope_class="private",
            scope_key=f"private:{creator.id}",
            owner_user_id=creator.id,
            comparison_json={"deterministic": True},
            lineage_digest="f" * 64,
        )
        db.add_all([comparison, private_comparison])
        db.execute(
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == organization.id)
            .where(OrganizationMembershipModel.user_id == remaining_owner.id)
        ).scalars().one().role = "owner"
        db.execute(
            select(OrganizationMembershipModel)
            .where(OrganizationMembershipModel.organization_id == organization.id)
            .where(OrganizationMembershipModel.user_id == creator.id)
        ).scalars().one().status = "removed"
        db.commit()
        creator_id, remaining_owner_id = creator.id, remaining_owner.id
        organization_id, organization_thesis_id = organization.id, organization_thesis.id
        private_thesis_id, comparison_id = private_thesis.id, comparison.id
        private_comparison_id = private_comparison.id

    with postgres_sessions() as db:
        creator_actor = user_context(db.get(UserModel, creator_id))
        with pytest.raises(HTTPException) as exc_info:
            get_thesis(db, creator_actor, organization_thesis_id)
        assert exc_info.value.status_code == 404
        assert delete_account(AccountDeleteRequest(confirmation="DELETE"), db, creator_actor).status == "pending_provider_deletion"

    with postgres_sessions() as db:
        assert db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == organization_thesis_id)).all()
        assert db.scalars(select(ThesisAssumptionModel).where(ThesisAssumptionModel.thesis_id == organization_thesis_id)).all()
        assert db.scalars(select(ThesisCatalystModel).where(ThesisCatalystModel.thesis_id == organization_thesis_id)).all()
        assert db.get(ResearchReportComparisonModel, comparison_id) is not None
        assert db.get(ResearchReportComparisonModel, private_comparison_id) is None
        assert not db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == private_thesis_id)).all()
        assert not db.scalars(select(ThesisAssumptionModel).where(ThesisAssumptionModel.thesis_id == private_thesis_id)).all()
        assert not db.scalars(select(ThesisCatalystModel).where(ThesisCatalystModel.thesis_id == private_thesis_id)).all()
        remaining_actor = user_context(db.get(UserModel, remaining_owner_id))
        assert get_thesis(db, remaining_actor, organization_thesis_id).id == organization_thesis_id
        assert delete_organization(db, remaining_actor, organization_id).id == organization_id

    with postgres_sessions() as db:
        assert not db.scalars(select(ThesisRevisionModel).where(ThesisRevisionModel.thesis_id == organization_thesis_id)).all()
        assert not db.scalars(select(ThesisAssumptionModel).where(ThesisAssumptionModel.thesis_id == organization_thesis_id)).all()
        assert not db.scalars(select(ThesisCatalystModel).where(ThesisCatalystModel.thesis_id == organization_thesis_id)).all()
        assert db.get(ResearchReportComparisonModel, comparison_id) is None


def test_postgres_visibility_change_and_evidence_mutation_serialize_on_the_thesis_row(postgres_sessions: sessionmaker) -> None:
    suffix = uuid4().hex[:12]
    with postgres_sessions() as db:
        owner = create_user(db, f"phase21d-scope-owner-{suffix}@example.test")
        org = OrganizationModel(
            id=f"org_phase21d_scope_pg_{suffix}",
            name="Phase 21D scope race organization",
            slug=f"phase21d-scope-pg-{suffix}",
            status="active",
            created_by_user_id=owner.id,
        )
        db.add(org)
        db.flush()
        thesis = SavedThesisModel(
            id=f"thesis_phase21d_scope_pg_{suffix}",
            owner_user_id=owner.id,
            organization_id=org.id,
            title="Scope serialization thesis",
            strategy_text="A scope change and evidence mutation share the thesis row lock.",
            protocols=["pendle"],
            assumptions_json={},
            visibility="organization",
        )
        db.add_all([
            OrganizationMembershipModel(
                id=f"membership_phase21d_scope_pg_{suffix}",
                organization_id=org.id,
                user_id=owner.id,
                role="owner",
                status="active",
            ),
            thesis,
        ])
        create_initial_revision(db, thesis, owner.id)
        db.commit()
        owner_id, thesis_id = owner.id, thesis.id

    barrier = Barrier(2)

    def change_scope() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, owner_id))
            barrier.wait(timeout=10)
            try:
                update_thesis(db, actor, thesis_id, ThesisUpdateRequest(visibility="private", expected_revision=1))
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    def add_evidence() -> int:
        with postgres_sessions() as db:
            actor = user_context(db.get(UserModel, owner_id))
            barrier.wait(timeout=10)
            try:
                create_assumption(
                    db,
                    actor,
                    thesis_id,
                    ResearchAssumptionCreateRequest(
                        statement="The serialized mutation is deliberately unverified.",
                        evidence_references=[{"unverified_reference": "PostgreSQL concurrency fixture"}],
                        expected_thesis_revision=1,
                    ),
                )
                return 200
            except HTTPException as exc:
                db.rollback()
                return exc.status_code

    with ThreadPoolExecutor(max_workers=2) as executor:
        outcomes = list(executor.map(lambda action: action(), (change_scope, add_evidence)))
    assert sorted(outcomes) == [200, 409]
    with postgres_sessions() as db:
        rows = db.scalars(
            select(ThesisRevisionModel)
            .where(ThesisRevisionModel.thesis_id == thesis_id)
            .order_by(ThesisRevisionModel.revision_number)
        ).all()
        assert [row.revision_number for row in rows] == [1, 2]


def _persist_report(db, report_id: str, owner_user_id: str, strategy: str, rating: str) -> None:
    analysis = AnalysisRequestModel(
        id=f"analysis_{report_id}",
        strategy_description=strategy,
        protocols=["pendle"],
        manual_inputs_json={},
        analysis_depth="standard",
        owner_user_id=owner_user_id,
        visibility="private",
    )
    report = ReportResponse(
        report_id=report_id,
        risk_rating=rating,
        executive_summary="Deterministic research summary.",
        strategy_description=strategy,
        protocols=["pendle"],
        assumptions=["Inputs are explicit."],
        missing_data=["Current utilization"],
        sections=[ReportSection(title="Risk Analysis", content="Deterministic section.")],
        sources=[SourceReference(title="Synthetic source", source_type="public_doc")],
        disclaimer="Educational research only.",
    )
    db.add_all([
        analysis,
        ReportModel(
            id=report_id,
            analysis_request_id=analysis.id,
            title="Phase 21D report",
            risk_rating=rating,
            summary=report.executive_summary,
            report_markdown="# report",
            report_json=report.model_dump(mode="json"),
            owner_user_id=owner_user_id,
            visibility="private",
        ),
    ])

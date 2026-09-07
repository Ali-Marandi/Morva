from datetime import date

import pytest

from morva.domain.core_hr import (
    Dependent,
    DependentRelationship,
    Education,
    EducationLevel,
    Experience,
    ExperienceType,
)


def test_education_is_immutable_and_explicit() -> None:
    education = Education(
        employee_no="EMP-1",
        level=EducationLevel.MASTER,
        field_of_study="Educational Management",
        institution="University",
        completed_on=date(1403, 6, 1),
        certificate_reference="CERT-1",
    )
    assert education.employee_no == "EMP-1"
    with pytest.raises(AttributeError):
        education.employee_no = "EMP-2"  # type: ignore[misc]


def test_experience_effective_boundaries() -> None:
    experience = Experience(
        employee_no="EMP-1",
        experience_type=ExperienceType.TEACHING,
        organization_name="School A",
        starts_on=date(1400, 1, 1),
        ends_on=date(1402, 12, 29),
    )
    experience.validate()
    assert experience.active_on(date(1400, 1, 1))
    assert experience.active_on(date(1402, 12, 29))
    assert not experience.active_on(date(1403, 1, 1))


def test_experience_rejects_invalid_range() -> None:
    experience = Experience(
        employee_no="EMP-1",
        experience_type=ExperienceType.GOVERNMENT,
        organization_name="Org",
        starts_on=date(1403, 6, 1),
        ends_on=date(1403, 5, 31),
    )
    with pytest.raises(ValueError, match="ends_on cannot precede starts_on"):
        experience.validate()


def test_dependent_effective_boundaries_and_range_validation() -> None:
    dependent = Dependent(
        employee_no="EMP-1",
        relationship=DependentRelationship.CHILD,
        name="Dependent A",
        valid_from=date(1404, 1, 1),
        valid_to=date(1404, 12, 29),
    )
    dependent.validate()
    assert dependent.active_on(date(1404, 1, 1))
    assert dependent.active_on(date(1404, 12, 29))
    assert not dependent.active_on(date(1405, 1, 1))

    invalid = Dependent(
        employee_no="EMP-1",
        relationship=DependentRelationship.SPOUSE,
        name="Dependent B",
        valid_from=date(1404, 7, 1),
        valid_to=date(1404, 6, 30),
    )
    with pytest.raises(ValueError, match="valid_to cannot precede valid_from"):
        invalid.validate()

"""
Pytest configuration and fixtures
"""
import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))


@pytest.fixture
def test_data_dir():
    """Fixture for test data directory"""
    return Path(__file__).parent / "test_data"


@pytest.fixture
def sample_text():
    """Fixture for sample text"""
    return """
    Student academic probation is a status assigned to students whose grade point 
    average falls below 2.0 in any term. Students on probation must meet with an 
    academic advisor and develop an academic improvement plan.
    """


@pytest.fixture
def sample_documents():
    """Fixture for sample documents"""
    return [
        {"content": "Academic probation occurs when GPA < 2.0", "source": "doc1.pdf"},
        {"content": "Automatic dismissal happens after 2 consecutive terms on probation", "source": "doc2.pdf"},
        {"content": "Students can appeal dismissal within 30 days", "source": "doc3.pdf"},
    ]


def pytest_configure(config):
    """Pytest configuration hook"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow"
    )

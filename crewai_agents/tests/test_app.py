import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock, mock_open
import os
import shutil
import io

# client fixture is from conftest.py

def test_health_check(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_upload_files_success(client: TestClient, setup_teardown_knowledge_dir):
    # Create a dummy file content
    file_content = b"col1,col2\nval1,val2"
    
    # FastAPI's TestClient handles file uploads by passing a tuple:
    # (filename, file-like-object, content_type)
    files = [
        ("test1.csv", io.BytesIO(file_content), "text/csv"),
        ("test2.csv", io.BytesIO(file_content), "text/csv")
    ]

    # The 'files' parameter in client.post should be a list of such tuples
    # but the key for each file should be 'files' as defined in the endpoint `File(...)`
    # and expected by `request.files.getlist("files")` if that was used,
    # or how `List[UploadFile] = File(...)` processes it.
    # For TestClient, it's often simpler to pass a dictionary if the endpoint expects named files,
    # but for `List[UploadFile]`, it's `{'files': [tuple1, tuple2]}`

    # Correct way to send multiple files for List[UploadFile]
    # Each file needs to be under the same key 'files'
    upload_data = []
    for filename, file_obj, content_type in files:
        upload_data.append(('files', (filename, file_obj, content_type)))

    response = client.post("/upload_files", files=upload_data)
    
    assert response.status_code == 200
    response_json = response.json()
    assert "filenames" in response_json
    assert "paths" in response_json
    assert sorted(response_json["filenames"]) == sorted(["test1.csv", "test2.csv"])
    
    # Check if files were created in the knowledge directory
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    assert os.path.exists(os.path.join(knowledge_dir, "test1.csv"))
    assert os.path.exists(os.path.join(knowledge_dir, "test2.csv"))

def test_upload_files_failure(client: TestClient, setup_teardown_knowledge_dir):
    file_content = b"col1,col2\nval1,val2"
    files_data = [('files', ("test_fail.csv", io.BytesIO(file_content), "text/csv"))]

    with patch("shutil.copyfileobj", side_effect=IOError("Disk full")):
        response = client.post("/upload_files", files=files_data)
    
    assert response.status_code == 500
    assert "Error uploading test_fail.csv: Disk full" in response.json()["detail"]

def test_analyze_data_no_csv(client: TestClient, setup_teardown_knowledge_dir):
    # Ensure knowledge directory is empty or has no CSVs
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    for item in os.listdir(knowledge_dir):
        if item.endswith(".csv"):
            os.remove(os.path.join(knowledge_dir, item))
            
    response = client.post("/analyze_data", json={"query": "What are the sales trends?"})
    assert response.status_code == 404
    assert "No CSV file found in the knowledge folder" in response.json()["detail"]

@patch("app.create_data_analysis_crew") # Patching where it's used in app.py
def test_analyze_data_success(mock_create_crew, client: TestClient, setup_teardown_knowledge_dir):
    # Create a dummy CSV in the knowledge folder
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    dummy_csv_path = os.path.join(knowledge_dir, "dummy_data.csv")
    with open(dummy_csv_path, "w") as f:
        f.write("header1,header2\ndata1,data2")

    mock_crew_instance = MagicMock()
    mock_result = MagicMock()
    mock_result.raw = "This is a raw analysis result."
    mock_crew_instance.kickoff.return_value = mock_result
    mock_create_crew.return_value = mock_crew_instance

    response = client.post("/analyze_data", json={"query": "Analyze this."})

    assert response.status_code == 200
    assert response.json() == {"result": "This is a raw analysis result."}
    
    # Check that create_data_analysis_crew was called with the path to the first CSV
    # Note: os.path.join("", "dummy_data.csv") becomes "dummy_data.csv" on Unix-like
    # and might be different on Windows. The key is it's called with the filename.
    # The app.py code `os.path.join("", csv_files[0])` might be better as `os.path.join("knowledge", csv_files[0])`
    # for robustness, but we test the current implementation.
    mock_create_crew.assert_called_once_with("dummy_data.csv") 
    mock_crew_instance.kickoff.assert_called_once_with(inputs={"question": "Analyze this."})

@patch("app.create_data_analysis_crew")
def test_analyze_data_crew_execution_failure(mock_create_crew, client: TestClient, setup_teardown_knowledge_dir):
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    dummy_csv_path = os.path.join(knowledge_dir, "dummy_data.csv")
    with open(dummy_csv_path, "w") as f:
        f.write("header1,header2\ndata1,data2")

    mock_crew_instance = MagicMock()
    mock_crew_instance.kickoff.side_effect = Exception("Crew failed unexpectedly")
    mock_create_crew.return_value = mock_crew_instance

    response = client.post("/analyze_data", json={"query": "Analyze this."})
    assert response.status_code == 500
    assert "CrewAI execution failed: Crew failed unexpectedly" in response.json()["detail"]

@patch("app.create_data_analysis_crew", side_effect=FileNotFoundError("utils.py dependent file not found"))
def test_analyze_data_crew_creation_file_not_found(mock_create_crew_fnf, client: TestClient, setup_teardown_knowledge_dir):
    knowledge_dir = os.path.join(os.path.dirname(__file__), "..", "knowledge")
    dummy_csv_path = os.path.join(knowledge_dir, "dummy_data.csv")
    with open(dummy_csv_path, "w") as f:
        f.write("header1,header2\ndata1,data2")

    response = client.post("/analyze_data", json={"query": "Analyze this."})
    assert response.status_code == 404 # As per app.py's FileNotFoundError handling
    assert "utils.py dependent file not found" in response.json()["detail"]

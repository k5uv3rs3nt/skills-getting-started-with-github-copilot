"""
Tests for the Mergington High School API
"""
import pytest
from fastapi.testclient import TestClient
from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the API"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to initial state before each test"""
    activities.clear()
    activities.update({
        "Soccer Team": {
            "description": "Join the school soccer team and compete in regional tournaments",
            "schedule": "Mondays and Wednesdays, 4:00 PM - 6:00 PM",
            "max_participants": 25,
            "participants": ["alex@mergington.edu", "sarah@mergington.edu"]
        },
        "Basketball Club": {
            "description": "Practice basketball skills and participate in friendly matches",
            "schedule": "Tuesdays and Thursdays, 4:00 PM - 5:30 PM",
            "max_participants": 15,
            "participants": ["james@mergington.edu", "emily@mergington.edu"]
        },
        "Art Club": {
            "description": "Explore various art mediums including painting, drawing, and sculpture",
            "schedule": "Wednesdays, 3:30 PM - 5:00 PM",
            "max_participants": 18,
            "participants": ["lily@mergington.edu", "noah@mergington.edu"]
        }
    })
    yield


class TestRootEndpoint:
    """Tests for the root endpoint"""
    
    def test_root_redirects(self, client):
        """Test that root endpoint redirects to static/index.html"""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint"""
    
    def test_get_activities(self, client):
        """Test retrieving all activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Art Club" in data
        assert len(data) == 3
    
    def test_activity_structure(self, client):
        """Test that activities have correct structure"""
        response = client.get("/activities")
        data = response.json()
        
        soccer = data["Soccer Team"]
        assert "description" in soccer
        assert "schedule" in soccer
        assert "max_participants" in soccer
        assert "participants" in soccer
        assert isinstance(soccer["participants"], list)


class TestSignupEndpoint:
    """Tests for the POST /activities/{activity_name}/signup endpoint"""
    
    def test_successful_signup(self, client):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Soccer Team/signup?email=new.student@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Signed up" in data["message"]
        assert "new.student@mergington.edu" in data["message"]
        
        # Verify participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "new.student@mergington.edu" in activities_data["Soccer Team"]["participants"]
    
    def test_signup_nonexistent_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_duplicate_signup(self, client):
        """Test that duplicate signup is prevented"""
        email = "alex@mergington.edu"
        response = client.post(
            f"/activities/Soccer Team/signup?email={email}"
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]
    
    def test_signup_updates_participant_list(self, client):
        """Test that signup adds to participant list"""
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Art Club"]["participants"])
        
        # Sign up new participant
        client.post("/activities/Art Club/signup?email=newstudent@mergington.edu")
        
        # Verify count increased
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Art Club"]["participants"])
        assert final_count == initial_count + 1


class TestUnregisterEndpoint:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint"""
    
    def test_successful_unregister(self, client):
        """Test successful unregister from an activity"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=alex@mergington.edu"
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
        assert "alex@mergington.edu" in data["message"]
        
        # Verify participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert "alex@mergington.edu" not in activities_data["Soccer Team"]["participants"]
    
    def test_unregister_nonexistent_activity(self, client):
        """Test unregister from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]
    
    def test_unregister_not_registered(self, client):
        """Test unregister when student is not registered"""
        response = client.delete(
            "/activities/Soccer Team/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
    
    def test_unregister_updates_participant_list(self, client):
        """Test that unregister removes from participant list"""
        # Get initial count
        initial_response = client.get("/activities")
        initial_count = len(initial_response.json()["Basketball Club"]["participants"])
        
        # Unregister a participant
        client.delete("/activities/Basketball Club/unregister?email=james@mergington.edu")
        
        # Verify count decreased
        final_response = client.get("/activities")
        final_count = len(final_response.json()["Basketball Club"]["participants"])
        assert final_count == initial_count - 1


class TestIntegration:
    """Integration tests for complete workflows"""
    
    def test_signup_and_unregister_workflow(self, client):
        """Test complete workflow of signing up and then unregistering"""
        email = "workflow@mergington.edu"
        activity = "Art Club"
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify participant is in list
        get_response = client.get("/activities")
        assert email in get_response.json()[activity]["participants"]
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify participant is removed
        final_response = client.get("/activities")
        assert email not in final_response.json()[activity]["participants"]
    
    def test_multiple_activities_signup(self, client):
        """Test signing up for multiple activities"""
        email = "multi@mergington.edu"
        
        # Sign up for multiple activities
        client.post(f"/activities/Soccer Team/signup?email={email}")
        client.post(f"/activities/Basketball Club/signup?email={email}")
        client.post(f"/activities/Art Club/signup?email={email}")
        
        # Verify participant is in all activities
        response = client.get("/activities")
        data = response.json()
        assert email in data["Soccer Team"]["participants"]
        assert email in data["Basketball Club"]["participants"]
        assert email in data["Art Club"]["participants"]

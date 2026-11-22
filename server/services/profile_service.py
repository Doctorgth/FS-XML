from typing import Dict, List
from server.database.models import ProfileModel
from server.database.repository import DatabaseRepository


class ProfileService:
    def __init__(self, repo: DatabaseRepository) -> None:
        self.repo = repo

    def list_profiles(self, project_id: int) -> List[ProfileModel]:
        return self.repo.list_profiles(project_id)

    def create_profile(self, project_id: int, name: str) -> ProfileModel:
        return self.repo.create_profile(project_id, name)

    def get_rules(self, profile_id: int) -> Dict[str, str]:
        return self.repo.get_profile_rules(profile_id)

    def set_rule(self, profile_id: int, rel_path: str, state: str) -> None:
        self.repo.set_profile_file_rule(profile_id, rel_path, state)

    def set_rules_bulk(self, profile_id: int, rules: List[tuple]) -> None:
        self.repo.set_profile_file_rules_bulk(profile_id, rules)
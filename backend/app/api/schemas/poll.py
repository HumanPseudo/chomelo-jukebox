from datetime import datetime

from pydantic import BaseModel, Field


class PollCreate(BaseModel):
    question: str = Field(min_length=1, max_length=300)
    options: list[str] = Field(min_length=2, max_length=20)
    closes_at: datetime | None = None

    @property
    def clean_options(self) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for text in self.options:
            text = text.strip()
            if not text or text in seen:
                continue
            seen.add(text)
            result.append(text[:200])
        return result


class PollVoteRequest(BaseModel):
    option_id: int


class PollOptionOut(BaseModel):
    id: int
    text: str
    votes: int = 0


class PollOut(BaseModel):
    id: int
    question: str
    status: str
    closes_at: datetime | None = None
    created_at: datetime
    created_by: int
    options: list[PollOptionOut]
    my_option_id: int | None = None
    total_votes: int = 0

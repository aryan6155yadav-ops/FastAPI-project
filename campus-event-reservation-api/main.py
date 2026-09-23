from enum import Enum

from fastapi import FastAPI, HTTPException, status
from pydantic import EmailStr
from sqlmodel import Field, SQLModel, Session, create_engine, select


# =========================================================
# ENUMS
# =========================================================

class EventStatus(str, Enum):
    OPEN = "Open"
    CLOSED = "Closed"


# =========================================================
# DATABASE MODELS
# =========================================================

class Event(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    title: str
    venue: str
    capacity: int
    organizer: str
    status: EventStatus


class Reservation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    event_id: int
    student_name: str
    roll_number: str
    email: EmailStr


# =========================================================
# REQUEST MODELS
# =========================================================

class EventCreate(SQLModel):
    title: str = Field(min_length=1)
    venue: str = Field(min_length=1)
    capacity: int = Field(gt=0)
    organizer: str = Field(min_length=1)
    status: EventStatus


class ReservationCreate(SQLModel):
    student_name: str = Field(min_length=1)
    roll_number: str = Field(min_length=1)
    email: EmailStr


# =========================================================
# RESPONSE MODEL
# =========================================================

class AvailabilityResponse(SQLModel):
    capacity: int
    booked: int
    remaining: int


# =========================================================
# DATABASE CONFIGURATION
# =========================================================

DATABASE_URL = "sqlite:///./event_reservation.db"

engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)


# =========================================================
# FASTAPI APPLICATION
# =========================================================

app = FastAPI(
    title="Campus Event Seat Reservation API",
    description="REST API for managing campus events and student reservations",
    version="1.0.0"
)


# =========================================================
# CREATE DATABASE TABLES AT STARTUP
# =========================================================

@app.on_event("startup")
def create_tables():
    SQLModel.metadata.create_all(engine)


# =========================================================
# EVENT APIs
# =========================================================

# 1. POST /events
# Create a new event
@app.post(
    "/events",
    response_model=Event,
    status_code=status.HTTP_201_CREATED
)
def create_event(event: EventCreate):

    with Session(engine) as session:

        db_event = Event.model_validate(event)

        session.add(db_event)
        session.commit()
        session.refresh(db_event)

        return db_event


# 2. GET /events
# Return all events
@app.get("/events", response_model=list[Event])
def get_events():

    with Session(engine) as session:

        statement = select(Event)

        events = session.exec(statement).all()

        return events


# 3. GET /events/{event_id}
# Return a specific event
@app.get("/events/{event_id}", response_model=Event)
def get_event(event_id: int):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        return event


# 4. PUT /events/{event_id}
# Update event information
@app.put("/events/{event_id}", response_model=Event)
def update_event(
    event_id: int,
    updated_event: EventCreate
):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Count current reservations
        statement = select(Reservation).where(
            Reservation.event_id == event_id
        )

        reservations = session.exec(statement).all()

        booked = len(reservations)

        # Do not allow capacity below existing bookings
        if updated_event.capacity < booked:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Capacity cannot be less than existing bookings ({booked})"
            )

        event.title = updated_event.title
        event.venue = updated_event.venue
        event.capacity = updated_event.capacity
        event.organizer = updated_event.organizer
        event.status = updated_event.status

        session.add(event)
        session.commit()
        session.refresh(event)

        return event


# 5. DELETE /events/{event_id}
# Delete an event
@app.delete("/events/{event_id}")
def delete_event(event_id: int):

    with Session(engine) as session:

        event = session.get(Event, event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # Delete reservations belonging to this event
        statement = select(Reservation).where(
            Reservation.event_id == event_id
        )

        reservations = session.exec(statement).all()

        for reservation in reservations:
            session.delete(reservation)

        session.delete(event)

        session.commit()

        return {
            "message": "Event deleted successfully",
            "id": event_id
        }


# =========================================================
# RESERVATION APIs
# =========================================================

# 6. POST /events/{event_id}/reserve
# Create a reservation
@app.post(
    "/events/{event_id}/reserve",
    response_model=Reservation,
    status_code=status.HTTP_201_CREATED
)
def create_reservation(
    event_id: int,
    reservation: ReservationCreate
):

    with Session(engine) as session:

        # -------------------------------------------------
        # STEP 1: VERIFY EVENT EXISTS
        # -------------------------------------------------

        event = session.get(Event, event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        # -------------------------------------------------
        # STEP 2: VERIFY EVENT IS OPEN
        # -------------------------------------------------

        if event.status != EventStatus.OPEN:

            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Reservations are closed for this event"
            )

        # -------------------------------------------------
        # STEP 3: COUNT EXISTING RESERVATIONS
        # -------------------------------------------------

        statement = select(Reservation).where(
            Reservation.event_id == event_id
        )

        existing_reservations = session.exec(statement).all()

        booked = len(existing_reservations)

        # -------------------------------------------------
        # STEP 4: CHECK EVENT CAPACITY
        # -------------------------------------------------

        if booked >= event.capacity:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Event is full. No seats available."
            )

        # -------------------------------------------------
        # STEP 5: CREATE RESERVATION
        # -------------------------------------------------
        # event_id is supplied directly here.
        # This fixes the previous validation error.

        db_reservation = Reservation(
            event_id=event_id,
            student_name=reservation.student_name,
            roll_number=reservation.roll_number,
            email=reservation.email
        )

        session.add(db_reservation)
        session.commit()
        session.refresh(db_reservation)

        return db_reservation


# 7. GET /events/{event_id}/reservations
# Return all reservations for an event
@app.get(
    "/events/{event_id}/reservations",
    response_model=list[Reservation]
)
def get_event_reservations(event_id: int):

    with Session(engine) as session:

        # Verify event exists
        event = session.get(Event, event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        statement = select(Reservation).where(
            Reservation.event_id == event_id
        )

        reservations = session.exec(statement).all()

        return reservations


# 8. DELETE /reservations/{reservation_id}
# Cancel a reservation
@app.delete("/reservations/{reservation_id}")
def delete_reservation(reservation_id: int):

    with Session(engine) as session:

        reservation = session.get(
            Reservation,
            reservation_id
        )

        if reservation is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Reservation not found"
            )

        session.delete(reservation)

        session.commit()

        return {
            "message": "Reservation cancelled successfully",
            "id": reservation_id
        }


# 9. GET /events/{event_id}/availability
# Return seat availability
@app.get(
    "/events/{event_id}/availability",
    response_model=AvailabilityResponse
)
def get_event_availability(event_id: int):

    with Session(engine) as session:

        # Verify event exists
        event = session.get(Event, event_id)

        if event is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Event not found"
            )

        statement = select(Reservation).where(
            Reservation.event_id == event_id
        )

        reservations = session.exec(statement).all()

        booked = len(reservations)

        remaining = event.capacity - booked

        return {
            "capacity": event.capacity,
            "booked": booked,
            "remaining": remaining
        }
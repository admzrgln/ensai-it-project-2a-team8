# Screening API tests

Tests done manually with Swagger on __/11/2026, on a database created with `database/schema.sql` and `database/seed.sql`.

Since the first version of these tests (29/10/2026), the body of a screening only contains
`id_room`, `id_movie` and `date_time`:

- there is no price any more: prices come from the tariff table;
- the administrator is read in the JWT token;
- the number of available seats is computed from the capacity of the room.

## 1. GET requests (public)

| Request | Result |
|---|---|
| GET /screenings/ | 200 - Returns the 3 screenings of the seed, with the movie title |
| GET /screenings/movie/1 | 200 - Returns the Inception screening |
| GET /screenings/1 | 200 - Screening found |
| GET /screenings/99999 | 404 - Screening not found |

## 2. POST requests - Validation

Logged in as the administrator (`admin@cinema-demo.fr`), except for the last two lines.

| Test | Result |
|---|---|
| Movie ID doesn't exist (99999) | 400 - Movie 99999 not found |
| Room ID doesn't exist (99999) | 400 - Room 99999 not found |
| Screening date in the past | 400 - The screening must be in the future |
| Invalid date ("demain") | 422 - Not a valid datetime |
| Two screenings overlapping in the same room | 400 - Room already used (30 minutes are required between two screenings) |
| Logged in as a customer | 403 - Admin only |
| Without token | 401 - Not authenticated |

All these requests were rejected as expected.

## 3. Create / Update / Delete

Used room 5 (40 seats) to test the following operations.

- **POST /screenings/**: Created a screening for Inception on 05/03/2027 at 18:00 (`{"id_room": 5, "id_movie": 1, "date_time": "2027-03-05T18:00:00"}`). Status 201. The administrator comes from the token and the screening has 40 available seats (capacity of room 5).
- **PUT /screenings/{id}**: Changed the time from 18:00 to 21:00. Status 200.
- **GET /screenings/{id}**: Checked that the time was updated.
- **DELETE /screenings/{id}**: Deleted the screening. Status 200.
- **GET /screenings/{id}**: Returned 404 after deletion.

## 4. Remarks

The tested endpoints worked as expected. The validation checks in ScreeningService work correctly,
and only an administrator can create, update or delete a screening.

The test screening was removed after the tests.

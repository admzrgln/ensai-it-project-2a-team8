# Screening API tests

Tests done manually with Swagger on 29/10/2026.

## 1. GET requests

| Request | Result |
|---|---|
| GET /screenings/ | 200 - Returns all 3 screenings |
| GET /screenings/movie/1 | 200 - Returns Inception screening |
| GET /screenings/1 | 200 - Screening found |
| GET /screenings/99999 | 404 - Screening not found |

## 2. POST requests - Validation

Tested different cases to check the conditions in ScreeningService.

| Test | Result |
|---|---|
| Negative price (-5) | 400 |
| More available seats than room capacity (100 instead of 40) | 400 |
| Movie ID doesn't exist (99999) | 400 |
| Admin ID doesn't exist (99999) | 400 |
| Screening date in the past | 400 |
| Two screenings overlapping in the same room | 400 |

All these requests were rejected as expected.

## 3. Create / Update / Delete

Used room 5 to test the following operations.

- **POST /screenings/**: Created a screening for Inception on 05/11/2026 at 18:00, price 12.5, 40 seats. Status 201, new screening ID = 7.
- **PUT /screenings/7**: Changed the price from 12.5 to 10. Status 200.
- **GET /screenings/7**: Checked that the price was updated.
- **DELETE /screenings/7**: Deleted the screening. Status 200.
- **GET /screenings/7**: Returned 404 after deletion.

## 4. Remarks

The tested endpoints worked as expected. The validation checks in ScreeningService also seem to work correctly.

The test screening (ID 7) was removed after the tests.  
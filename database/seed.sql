
-- Initial data for testing the cinema application

-- Movies
INSERT INTO public.movie
    (id_movie, title, duration, genre, external_id, poster_url)
VALUES
    (1, 'Inception', 148, 'Science-fiction', 'tt1375666', 'https://example.com/inception.jpg'),
    (2, 'Interstellar', 169, 'Science-fiction', 'tt0816692', 'https://example.com/interstellar.jpg'),
    (3, 'The Dark Knight', 152, 'Action', 'tt0468569', 'https://example.com/dark-knight.jpg');


-- Rooms
INSERT INTO public.room
    (id_room, type, number, capacity)
VALUES
    (1, 'Standard', 1, 120),
    (2, 'Standard', 2, 100),
    (3, 'IMAX', 3, 250),
    (4, '3D', 4, 150),
    (5, 'VIP', 5, 40);


-- Test administrator
-- This account is only used to reference an admin in test data.
-- The password is a placeholder, not a real login password.
INSERT INTO public.app_user
    (id_user, first_name, last_name, email, password, role, is_ensai_student)
VALUES
    (1, 'Test', 'Admin', 'admin-demo@example.invalid',
     'ACCOUNT_DISABLED_NO_LOGIN', 'admin', FALSE);


-- Screenings
INSERT INTO public.screening
    (id_screening, id_room, id_movie, id_admin,
     date_time, base_price, available_seats)
VALUES
    (1, 1, 1, 1, '2027-01-15 20:30:00', 12.50, 120),
    (2, 2, 3, 1, '2027-01-16 20:00:00', 11.00, 100),
    (3, 3, 2, 1, '2027-01-15 19:00:00', 15.00, 250);


-- Synchronize identity sequences after inserting explicit IDs
SELECT setval(
    pg_get_serial_sequence('public.movie', 'id_movie'),
    (SELECT MAX(id_movie) FROM public.movie)
);

SELECT setval(
    pg_get_serial_sequence('public.room', 'id_room'),
    (SELECT MAX(id_room) FROM public.room)
);

SELECT setval(
    pg_get_serial_sequence('public.app_user', 'id_user'),
    (SELECT MAX(id_user) FROM public.app_user)
);

SELECT setval(
    pg_get_serial_sequence('public.screening', 'id_screening'),
    (SELECT MAX(id_screening) FROM public.screening)
);

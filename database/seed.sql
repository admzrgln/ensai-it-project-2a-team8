

-- Ensai Cinema Club - demo data


INSERT INTO public.movie
    (id_movie, title, duration, genre, external_id, poster_url)
VALUES
    (1, 'Inception', 148, 'Science-fiction', 'tt1375666', 'https://example.com/inception.jpg'),
    (2, 'Interstellar', 169, 'Science-fiction', 'tt0816692', 'https://example.com/interstellar.jpg'),
    (3, 'The Dark Knight', 152, 'Action', 'tt0468569', 'https://example.com/dark-knight.jpg');


INSERT INTO public.room
    (id_room, number, capacity)
VALUES
    (1, 1, 120),
    (2, 2, 100),
    (3, 3, 250),
    (4, 4, 150),
    (5, 5, 40);


INSERT INTO public.app_user
    (id_user, first_name, last_name, email, password, salt,
     date_of_birth, role, is_ensai_student)
VALUES
    (1, 'Demo', 'Admin', 'admin@cinema-demo.fr',
     '6ff1a359164293e245b42318b67f1ae81ca314db514102c4259d9a2f26d9e593', 'demo-salt-admin',
     '1990-01-01', 'admin', FALSE),
    (2, 'Demo', 'Customer', 'customer@cinema-demo.fr',
     '25b4a1ec05b265ab687e18d7cce470446ec545335e95877f890e77e4d714b679', 'demo-salt-customer',
     '2004-03-01', 'customer', FALSE);


INSERT INTO public.screening
    (id_screening, id_room, id_movie, id_admin, date_time, available_seats)
VALUES
    (1, 1, 1, 1, '2027-01-15 20:30:00', 120),
    (2, 2, 3, 1, '2027-01-16 20:00:00', 100),
    (3, 3, 2, 1, '2027-01-15 19:00:00', 250);


INSERT INTO public.tariff
    (code, label, price, min_age, max_age, requires_ensai, requires_student)
VALUES
    ('full',   'Full price',    11.50, NULL, NULL, FALSE, FALSE),
    ('child',  'Under 14',       6.00, NULL, 13,   FALSE, FALSE),
    ('senior', 'Over 65',        9.50, 65,   NULL, FALSE, FALSE),
    ('ensai',  'ENSAI Student',  7.80, NULL, NULL, TRUE,  FALSE);


SELECT setval(pg_get_serial_sequence('public.movie', 'id_movie'),
              (SELECT MAX(id_movie) FROM public.movie));

SELECT setval(pg_get_serial_sequence('public.room', 'id_room'),
              (SELECT MAX(id_room) FROM public.room));

SELECT setval(pg_get_serial_sequence('public.app_user', 'id_user'),
              (SELECT MAX(id_user) FROM public.app_user));

SELECT setval(pg_get_serial_sequence('public.screening', 'id_screening'),
              (SELECT MAX(id_screening) FROM public.screening));
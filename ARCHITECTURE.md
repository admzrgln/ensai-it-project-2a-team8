# Architecture 

# Architecture

```mermaid
---
title: Quick Architecture overview
---
    graph LR
    USR((User))
    DB[("fa:fa-database App Database \n (PostgreSQL)" )]
    API(fa:fa-python API / Controllers \n FastAPI)
    SVC(fa:fa-python Services)
    DAO(fa:fa-python DAO)
    OMDB[(fa:fa-database OMDb)]
    OMDBAPI(OMDb API)

    USR<--->API
        subgraph Python app
            API<-->SVC<-->DAO
        end
    DAO<--->DB
    OMDBAPI <--> OMDB
    SVC <--> OMDBAPI
```

- **Controllers** (`backend/src/Controller`): the routes of the API. They read the requests, check the JWT token and the role, and call the services.
- **Services** (`backend/src/Service`): the business rules (prices, seats left, screening overlaps, accounting).
- **DAO** (`backend/src/DAO`): the SQL queries to the PostgreSQL database.
- **Model** (`backend/src/Model`): the classes used by all the layers (Movie, Screening, Booking...).
- **OMDb API**: used by `OmdbClient` to search and import movies.
# PubMedIQ — Plain English Guide to Testing

> A simple, non-technical guide explaining how we test the PubMedIQ backend, why we test it, what each test category does, and what our results mean.

---

## 1. Overview: What is Software Testing?

Think of PubMedIQ like a complex medical search engine. When a user asks a medical question, many different parts of our software work together:
1. The app checks who you are (authentication).
2. It breaks down your medical question (query understanding).
3. It searches scientific papers on PubMed.
4. It organizes and ranks the best papers.
5. It generates a clear, cited AI summary.
6. It saves your search history into our database.

**Testing** is like running automated quality inspection checks on every single piece of this system before it goes live. 

We ran a total of **339 automated tests**, and **100% of them passed successfully**.

---

## 2. The 4 Testing Categories Explained Simply

We divide our tests into 4 distinct levels, moving from small individual components up to real database interactions.

```
       ┌─────────────────────────────────────────┐
       │   4. Integration Tests (PostgreSQL DB)  │  16 Tests
       ├─────────────────────────────────────────┤
       │   3. API Endpoint Tests (Web API)       │  34 Tests
       ├─────────────────────────────────────────┤
       │   2. Agent Tests (AI Workflow Pipeline) │   6 Tests
       ├─────────────────────────────────────────┤
       │   1. Unit Tests (Individual Logic)      │ 283 Tests
       └─────────────────────────────────────────┘
```

---

### Category 1: Unit Tests (283 Tests)

* **What it means in plain English:**  
  Testing the smallest possible building blocks in complete isolation. We do not connect to any real database or internet services here. We just test mathematical formulas, rules, and helper functions to make sure they return correct answers.

* **Real-world analogy:**  
  Testing individual engine parts (like checking if a spark plug sparks or if a gear turns) before assembling the car.

* **Examples of what we tested:**
  * **Password Hashing:** Making sure user passwords are encrypted securely using Argon2 encryption so plain passwords are never saved.
  * **JWT Security Tokens:** Making sure login security tokens are correctly formatted, signed, and expire after 30 minutes.
  * **Search Formula (RRF Scoring):** Checking that our scientific paper ranking algorithm gives higher priority to papers found in multiple sources.
  * **Input Rules:** Making sure search queries that are too short (less than 3 characters) are rejected immediately.

* **Result:** **283 Passed (0 Failed)**

---

### Category 2: Agent Tests / AI Workflow Pipeline (6 Tests)

* **What it means in plain English:**  
  Testing the blueprint of our AI decision-making pipeline (built with a framework called *LangGraph*). This checks that all 11 steps of our AI research pipeline are connected in the exact right order.

* **Real-world analogy:**  
  Checking an assembly line diagram to make sure station 1 feeds into station 2, and that if a quality problem is found, the item loops back for refinement.

* **Examples of what we tested:**
  * Making sure the AI pipeline starts at **Query Understanding**.
  * Making sure all 11 AI workflow steps (concept extraction, keyword search, MeSH retrieval, fusion, re-ranking, quality check, AI summary) are correctly wired together.
  * Making sure that if the search results aren't good enough, the pipeline automatically loops back to refine the query.

* **Result:** **6 Passed (0 Failed)**

---

### Category 3: API Endpoint Tests (34 Tests)

* **What it means in plain English:**  
  Testing our web interface (the HTTP URL endpoints that frontend apps or web browsers call). We test what happens when a user clicks "Register", "Login", or "Search".

* **Real-world analogy:**  
  Testing the front counter of a bank — checking if the clerk accepts valid deposit forms, gives correct receipts, and politely turns away forms with missing information.

* **Examples of what we tested:**
  * **`POST /api/v1/auth/register`**: Registering a new account returns a `201 Created` HTTP status code.
  * **Duplicate Emails**: Trying to register an email that already exists returns an error instead of creating a duplicate.
  * **`POST /api/v1/search`**: Sending a valid medical question returns structured search results.
  * **Error Messages**: If something goes wrong unexpectedly, the system returns a safe, clean error message (`500 Internal Error`) without leaking sensitive system details.

* **Result:** **34 Passed (0 Failed)**

---

### Category 4: Integration Tests (16 Tests — Real PostgreSQL Database)

* **What it means in plain English:**  
  Testing with a **real PostgreSQL database server** on your local machine (`pubmediq_test_db`). **No fake or mock data was used here.** Every test creates real database tables, inserts real user records, checks database rules, and then safely cleans up afterwards.

* **Real-world analogy:**  
  Taking the fully assembled car out onto a real test track to verify that steering, brakes, and acceleration work together on real pavement.

* **Examples of what we tested:**
  * **Real Account Creation:** Creating a real user in the database, verifying their unique ID (UUID), and verifying case-insensitive email matching.
  * **Search History Storage:** Saving real search records into a PostgreSQL JSONB column and retrieving user search history.
  * **Saved Papers (Bookmarks):** Saving a paper bookmark, checking if it is marked as saved, and unsaving it.
  * **End-to-End Auth Lifecycle:** Running a complete flow: Register a user → Login with password → Receive JWT token → Decode token and verify user identity in PostgreSQL.

* **Result:** **16 Passed (0 Failed)**

---

## 3. Summary of Total Results

| Testing Category | Purpose | DB Mode | Tests Executed | Passed | Failed | Time Taken |
|------------------|---------|---------|----------------|--------|--------|------------|
| **Unit Tests** | Isolated component logic | Mocked | 283 | 283 | 0 | ~9.7s |
| **Agent Pipeline** | LangGraph AI workflow structure | None | 6 | 6 | 0 | ~0.9s |
| **API Endpoints** | Web request & response rules | Mocked | 34 | 34 | 0 | ~2.8s |
| **Integration** | Real database tables & storage | PostgreSQL | 16 | 16 | 0 | ~1.6s |
| **FULL SUITE** | **Entire backend codebase** | **PostgreSQL** | **339** | **339** | **0** | **~13.8s** |

---

## 4. Why This Gives Us Confidence

1. **Zero Failures:** Every single feature in the test suite works exactly as intended.
2. **No Fake Database Data:** Our integration tests run against a real PostgreSQL database instance, proving our SQL queries, table schemas, and data structures work in reality.
3. **Automated Safety Net:** If anyone makes code changes in the future, running `pytest` will catch any accidental bugs or breaking changes in under 15 seconds.

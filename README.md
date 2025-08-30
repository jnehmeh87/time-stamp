# Timestamp Microservice

This is a simple API microservice that takes a date string or Unix timestamp and returns a JSON object with both the Unix timestamp and the UTC date string.

## Project Setup

### 1. Install Dependencies

To get started, clone the repository and install the necessary npm packages.

```sh
npm install
```

### 2. Run the Application

To start the local development server, run the following command. The application will be available at `http://localhost:3000`.

```sh
npm start
```

## Development Scripts

This project is equipped with tools to ensure code quality and a stable development process.

### Running Tests

To run the automated tests for the API, use:

```sh
npm test
```

### Linting and Formatting

To check for code quality issues, run the linter:

```sh
npm run lint
```

To automatically format all code to match the project's style guide, run:

```sh
npm run format
```

## API Usage

The main endpoint for this service is `/api/:date?`.

### Endpoint: `/api/:date?`

-   If the `:date` parameter is a valid date string (e.g., "2015-12-25"), it will return the corresponding Unix and UTC time.
-   If the `:date` parameter is a valid Unix timestamp, it will return the corresponding Unix and UTC time.
-   If the `:date` parameter is empty, it will return the current time.
-   If the `:date` parameter is invalid, it will return an error object.

#### Example Usage:

1.  **Request with a date string:**
    `/api/2015-12-25`

    **Response:**
    ```json
    {
      "unix": 1451001600000,
      "utc": "Fri, 25 Dec 2015 00:00:00 GMT"
    }
    ```

2.  **Request with a Unix timestamp:**
    `/api/1451001600000`

    **Response:**
    ```json
    {
      "unix": 1451001600000,
      "utc": "Fri, 25 Dec 2015 00:00:00 GMT"
    }
    ```

3.  **Request with an empty date:**
    `/api`

    **Response (will be the current time):**
    ```json
    {
      "unix": 1682611200000,
      "utc": "Fri, 27 Apr 2023 16:00:00 GMT"
    }
    ```

4.  **Request with an invalid date:**
    `/api/this-is-not-a-date`

    **Response:**
    ```json
    {
      "error": "Invalid Date"
    }
    ```

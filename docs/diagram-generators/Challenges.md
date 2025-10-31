sequenceDiagram
    participant User
    participant App
    participant Bedrock
    participant Model

    User->>App: Request
    App->>Bedrock: InvokeModel (API)
    
    alt Capacity Available
        Bedrock->>Model: Process request
        Model->>Bedrock: Response
        Bedrock->>App: Success
        App->>User: Response
    else Capacity Limited
        Bedrock->>App: ThrottlingException
        App->>User: Error/Timeout
    end

    Note over User,Model: Without Reliability Patterns:<br/>- Single region, Single model, Limited capacity

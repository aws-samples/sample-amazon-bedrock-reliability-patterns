# Pattern 8: Manual Multi-Model Fallback

```mermaid
%%{init: {'theme':'neutral'}}%%
flowchart TD
    Title[<b>Pattern 8: Manual Multi-Model Fallback</b>]
    
    Title --> App[Application]
    
    App --> Request[Complex Inference Request]
    Request --> Hierarchy[Model Hierarchy<br/>Ordered by Preference]
    
    Hierarchy --> Primary[Primary Model<br/>Claude 3.5 Sonnet v2<br/>Premium Quality]
    
    Primary --> Check1{Model Available?}
    Check1 -->|Yes| Success1[High-Quality Response]
    Check1 -->|No/Throttled| Fallback1[Fallback to Claude 3 Sonnet<br/>Standard Quality]
    
    Fallback1 --> Check2{Model Available?}
    Check2 -->|Yes| Success2[Standard Response]
    Check2 -->|No/Throttled| Fallback2[Fallback to Claude 3 Haiku<br/>Fast & Cost-Effective]
    
    Fallback2 --> Check3{Model Available?}
    Check3 -->|Yes| Success3[Fast Response]
    Check3 -->|No/Throttled| AllFailed[All Models Failed]
    
    Success1 --> Response[Model Response<br/>with Quality Indicator]
    Success2 --> Response
    Success3 --> Response
    AllFailed --> Error[Error Handling<br/>Retry or Alternative Strategy]
    
    %% Styling
    classDef custom fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef model fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef decision fill:#f0f8ff,stroke:#4682b4,stroke-width:2px
    classDef error fill:#ffe6e6,stroke:#d32f2f,stroke-width:2px
    classDef title fill:#f9f9f9,stroke:#333,stroke-width:2px,color:#000
    
    class Primary,Fallback1,Fallback2 model
    class Check1,Check2,Check3 decision
    class AllFailed,Error error
    class Title title
```

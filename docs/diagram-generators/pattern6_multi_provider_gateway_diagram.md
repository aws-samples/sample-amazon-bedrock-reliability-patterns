# Pattern 6: Multi-Provider Gateway

## AWS Solutions Guidance Architecture

![Multi-Provider Gateway Architecture](https://github.com/aws-solutions-library-samples/guidance-for-multi-provider-generative-ai-gateway-on-aws/raw/main/media/Gateway-Architecture-with-CloudFront.png)

*Source: [AWS Solutions Guidance for Multi-Provider Generative AI Gateway](https://github.com/aws-solutions-library-samples/guidance-for-multi-provider-generative-ai-gateway-on-aws)*

## Pattern Overview Diagram

```mermaid
%%{init: {'theme':'neutral'}}%%
flowchart TD
    Title[<b>Pattern 6: Multi-Provider Gateway</b>]
    
    Title --> App[Enterprise Application]
    
    App --> Gateway[Multi-Provider Gateway<br/>AWS Solutions Guidance]
    
    Gateway --> Router[Intelligent Request Router]
    Router --> LoadBalancer[Load Balancer & Failover Logic]
    
    LoadBalancer --> Bedrock[Amazon Bedrock<br/>Claude Models<br/>Nova Models<br/>Llama Models]
    LoadBalancer --> OpenAI[OpenAI<br/>GPT-4<br/>GPT-3.5]
    LoadBalancer --> Anthropic[Anthropic Direct<br/>Claude API]
    LoadBalancer --> Other[Other Providers<br/>Cohere<br/>AI21 Labs]
    
    Bedrock --> Response1[Provider Response]
    OpenAI --> Response2[Provider Response]
    Anthropic --> Response3[Provider Response]
    Other --> Response4[Provider Response]
    
    Response1 --> Unified[Unified Response Format]
    Response2 --> Unified
    Response3 --> Unified
    Response4 --> Unified
    
    Unified --> Features[Gateway Features<br/>Rate Limiting<br/>Cost Tracking<br/>Analytics<br/>Security]
    
    Features --> Output[Consistent API Response]
    
    %% Styling
    classDef custom fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef provider fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef feature fill:#f0f8ff,stroke:#4682b4,stroke-width:2px
    classDef title fill:#f9f9f9,stroke:#333,stroke-width:2px,color:#000
    
    class Gateway,Router,LoadBalancer custom
    class Bedrock,OpenAI,Anthropic,Other provider
    class Features,Unified feature
    class Title title
```

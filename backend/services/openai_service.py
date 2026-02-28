from openai import AsyncOpenAI
from config import settings


client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)


async def get_chat_response(message: str, model: str = "gpt-3.5-turbo") -> tuple[str, str]:
    """
    Call OpenAI API and get response.
    
    Args:
        message: User message
        model: OpenAI model to use (default: gpt-3.5-turbo)
    
    Returns:
        tuple: (response message, model used)
    """
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant."},
                {"role": "user", "content": message}
            ],
            max_tokens=500,
            temperature=0.7
        )
        
        reply = response.choices[0].message.content
        used_model = response.model
        
        return reply, used_model
        
    except Exception as e:
        raise Exception(f"OpenAI API call failed: {str(e)}")

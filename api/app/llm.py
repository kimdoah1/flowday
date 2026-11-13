
import os

from langchain_google_genai import ChatGoogleGenerativeAI


def ask_llm(prompt, output_model):
    """
    Gemini에 프롬프트를 전달하고
    지정한 Pydantic 모델 형태로 결과를 반환합니다.
    """

    api_key = os.getenv("GEMINI_API_KEY")
    model_name = os.getenv("LLM_MODEL")

    if not api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    if not model_name:
        raise ValueError("LLM_MODEL이 설정되지 않았습니다.")

    print("A. Gemini 모델 초기화", flush=True)

    llm = ChatGoogleGenerativeAI(
        model=model_name,
        google_api_key=api_key,
        temperature=0,
        max_output_tokens=8192
    )

    print("B. 구조화된 출력 설정", flush=True)

    structured_llm = llm.with_structured_output(
        output_model,
        method="json_schema"
    )

    print("C. Gemini 요청 전송", flush=True)

    result = structured_llm.invoke(prompt)

    print("D. Gemini 응답 수신 완료", flush=True)

    return result

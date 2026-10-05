import json

from app.services.process_service import generate_work_process


def main():
    question = input("Enter a work-related question: ").strip()

    worksheet = generate_work_process(question)

    print("\nGENERATED WORKSHEET\n")
    print(json.dumps(worksheet, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
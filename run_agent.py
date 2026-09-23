from dotenv import load_dotenv

from app.agent import SchedulingAgent


def main():
    load_dotenv()
    agent = SchedulingAgent(patient_id="demo_patient")
    print("Clinic Scheduler — type 'quit' to exit")
    while True:
        user = input("\nPatient: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        try:
            print("Agent:", agent.send(user))
        except Exception as exc:
            print("Agent error:", exc)


if __name__ == "__main__":
    main()

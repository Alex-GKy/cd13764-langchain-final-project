from health_bot import HealthBotSession, UserInputRequest


class HealthBotRunner:
    def __init__(self):
        self.session = None

    def start_conversation(self, initial_question: str):
        """Start a new conversation with the given question"""
        self.session = HealthBotSession(initial_question)
        self.run_conversation()

    def run_conversation(self):
        """Run the conversation loop using the generator interface"""
        if not self.session:
            return

        # Start the conversation generator
        conversation = self.session.run_conversation()
        response = None

        try:
            # Get the first response
            response = next(conversation)

            while True:
                if isinstance(response, str):
                    # AI message - display it
                    print(response)
                    # Get next response
                    response = next(conversation)

                elif isinstance(response, UserInputRequest):
                    # Bot wants input - get it and send back
                    user_input = self._get_user_input(response)
                    # Send user input back to generator and get next response
                    response = conversation.send(user_input)

        except StopIteration:
            # Conversation ended
            print("\nConversation ended.")

    def _get_user_input(self, request: UserInputRequest) -> str:
        """Get user input based on the request"""
        print(f"\n{request.prompt}")

        if request.options:
            options_str = "/".join(request.options)
            prompt = f"({options_str}): "
        else:
            prompt = "> "

        return input(prompt).strip()


# Add this to run the bot
if __name__ == "__main__":
    runner = HealthBotRunner()

    # Get initial question from user
    initial_question = input("What health topic would you like to research? ")

    # Start the conversation
    runner.start_conversation(initial_question)
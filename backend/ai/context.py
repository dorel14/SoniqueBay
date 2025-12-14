class ConversationContext:

    def __init__(self):
        self.messages = []
        self.last_intent = None
        self.mood = None

    def add_user(self, msg):
        self.messages.append({"role": "user", "content": msg})

    def add_agent(self, agent, msg):
        self.messages.append({
            "role": "assistant",
            "agent": agent,
            "content": msg
        })

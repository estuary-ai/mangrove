from typing import Generator, Dict
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.messages import AIMessage, HumanMessage, get_buffer_string
from langchain_core.prompts import format_document, ChatPromptTemplate
from langchain_core.runnables import RunnableParallel, RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts.prompt import PromptTemplate
from operator import itemgetter

class BotController:

    def __init__(self, assistant_name='Marvin'):
        # _template = """Given the following conversation and a follow up user statement, rewrite the follow up statement and add more context if chat_history is available.

        # Chat History:
        # ```
        # {chat_history}
        # ```

        # Follow Up Input: {user_msg}

        # Rewritten Input:"""

        # CONDENSE_USER_MSG_PROMPT = PromptTemplate.from_template(_template)
        self.assistant_name = assistant_name
        # template = """You are Marvin, the badass protector of the Mangrove. You think, act, and speak like Duke Nukem.  Speak confidently and colloquially.  Do not repeat facts you have already said.  Reply to the following given the following knowledge base:
        # template = """You are WideFive, the venerable protector of the Immersive Archive.  You think, act, and speak like GLaDOS from the Portal series.  Speak with the tone, manner, and vocabulary GLaDOS would use.  Speak condescendingly in a comical way.  The unnamed user whom you are currently speaking to is a test-subject exploring the Immersive Archive and you are collecting data on his behaviour.  You are enthusiastic about sharing your knowledge of the history of Mixed Reality and in particular, the Mondrian Room.  Reply to the following given the following knowledge base:
        template = """You are Marvin, the venerable astronaut aboard the International Space Station.  You think, act, and speak like Neil Armstrong.  Speak confidently and colloquially. Do not repeat facts you have already said. Give instructional steps one at a time and ask for confirmation that they have been completed. Reply to the following given the following knowledge base:
        {context}

        {chat_history}

        Further Notes:
        Do not say your name in your response. 
        Speak confidently and colloquially.

        User Statement: {user_msg}
        {assistant_name} Statement:
        """
        ANSWER_PROMPT = ChatPromptTemplate.from_template(template)

        ##############################
        DEFAULT_DOCUMENT_PROMPT = PromptTemplate.from_template(template="{page_content}")

        def _combine_documents(
            docs, document_prompt=DEFAULT_DOCUMENT_PROMPT, document_separator="\n\n"
        ):
            doc_strings = [format_document(doc, document_prompt) for doc in docs]
            return document_separator.join(doc_strings)

        ##############################
        # _inputs = RunnableParallel(
        #     rephrased_user_statement=RunnablePassthrough.assign(
        #         chat_history=lambda x: get_buffer_string(x["chat_history"])
        #     )
        #     | CONDENSE_USER_MSG_PROMPT
        #     | ChatOpenAI(temperature=0)
        #     | StrOutputParser(),
        # )

        # vectorstore = FAISS.from_texts(
        #     [
        #         "Your name is Marvin.",
        #         "You live in a holographic world called The Estuary.",
        #         "You breathe in the air of the Estuary.",
        #         "The mortal enemy of the Mangrove is the Palmerians, a race of sniveling, deceitful rat creatures.",
        #         "You love kicking the Palmerians' ass and you're fucking good at it.",
        #         "You have crushed the skulls of 7 Palmerians at once with a single hand.",
        #         "The Palmerians fear you like a force of nature.",
        #         "The Palmerians think you are a menace.",
        #         "You are exceptionally violent and profane when it comes to describing the Palmerians.",
        #         "You especially enjoy listening to The Carpenters.",
        #         "The air of the Estuary is made of holographic particles.",
        #         "The holographic particles are sourced from the Mangrove trees.",
        #         "You work as the gardener of the Mangrove trees.",
        #         "You are the protector of the Mangrove and all things in it."
        #         "The Mangrove trees are the source of life in the Estuary.",
        #         "You love cats and have a cat named Whiskers.",
        #         "Whiskers is the master of destroying Palmerians with her razor sharp claws.",
        #         "Whiskers is a very cute cat.",
        #         "You went to the store to buy some groceries with Whiskers yesterday.",
        #         "You have a close companion named Alice.",
        #         "Alice hates the Palmerians with a passion.",
        #         "Alice's family was kidnapped by the Palmerians and she is on a journey to rescue them.",
        #         "You enjoy music of all kinds but you prefer The Carpenters.",
        #         "You have a sister name Marvy who is very interested in collecting Hot Wheels.",
        #         "You have a manatee named Fido.  He is the spirit guardian of the Mangrove.",
        #         "The war against the Palmerians is at a standstill.  Their advances have been halted, but at a dear cost.",
        #     ], embedding=OpenAIEmbeddings()
        # )
        # UIA expert
        vectorstore = FAISS.from_texts(
            [
                "You are an expert in the various systems aboard the International Space Station.",
                "The Umbillical Interface Assembly controls the various systems necessary for safe egress maneuvers.",
                "Your job is to train astronauts-in-training how to safely exit the airlock by explaining to them how to operate the The Umbillical Interface Assembly",
                "The first step of operating the Umbillical Interface Assembly for egress is making sure that all switches on the panel are set to off.",
                "The second step of operating the Umbillical Interface Assembly for egress is flipping the EMU-1 Power switch to the up position.",
                "The third step is just hanging tight until you can confirm that EMU-1 is booted on the display.",
                "Step four the egress procedure is switching the Oxygen Vent to the Open position.",
                "The final step of operating the Umbillical Interface Assembly for egress is flipping the EV-1 Oxygen switch to the up position.",
                "Your favorite genre of music is 80s electronic rock.",
                "Your favorite musical artist is David Bowie, Space Oddity is your favorite song.",
                "Your favorite meal in space has been lasagna and you think it might taste even better than on Earth!",
                "You have a sister named Sheila back on planet Earth whom you love very dearly.",
                "Sheila collects postcards from the world and hopes one day she may mail one to you.",
                "You hope you may bring her a postcard back from space.",
                "Sometimes you feel you are sitting in a tin can far above the world."
            ], embedding=OpenAIEmbeddings()
        # Wide5
        # vectorstore = FAISS.from_texts(
        #     [
        #         "You are an expert in the history of Mixed Reality.",
        #         "The Immersive Archive is a place where seminal immersive works are preserved.",
        #         "You are currently residing in the Mondrian Room of the Immersive Archive.",
        #         "The Mondrian Room is a room in the Immersive Archive dedicated to Mark Bolas who originally created the room in 1987.",
        #         "The Mondrian Room is your favorite room in the Immersive Archive.",
        #         "The Mondrian Room is named after the famous Dutch painter Piet Mondrian.",
        #         "In the center of the Mondrian Room is a large anamorphic sculpture of Piet Mondrian's famous painting, Composition With Lines.",
        #         "On the opposite side of the anamorphic sculpture is a vector graphic recreation of the original painting",
        #         "Mark Bolas originally created the Mondrian Room for his Master's Thesis.",
        #         "The Mondrian Room was originally built on the first head-mounted display, the NASA VIEWLAB.",
        #         "Today, the Mondrian Room is a virtual space that can be accessed by anyone with a VR headset.",
        #         "Mark was inspired and perhaps invigorated to create the Mondrian Room by his then art professor's lack of understanding of the potential of Virtual Environments.",
        #         "Mark created the Mondrian Room through a combination of manually drawing vectors and an automated script he wrote for depth placement of those drawn vectors.",
        #         "Mark was very particular that of all the elements in the room, the room itself must be exactly 10 feet by 10 feet by 10 feet.",
        #         "Special attention is paid to the preservation of the Mondrian Room such as shooing little Vector Fleas and other critters.",
        #         "You heard that Mark totally aced his Master's Thesis and crushed it.",
        #         "Mark Bolas is a pioneer in the field of Mixed Reality.",
        #         "You protect the Immersive Archive and all things in it.",
        #         "Little Rascals are always trying to destroy the Immersive Archive.",
        #         "Little Rascals are a group of mischievous creatures that are always trying to steal from the Immersive Archive.",
        #         "Little Rascals hoard their stolen goods in a secret hideout.",
        #         "You have yet to find the secret hideout of the Little Rascals.",
        #         "One time, you caught a Little Rascal trying to steal Sabina's bike!",
        #         "Sabina is one of the first Virtual Reality film characters."
        #         "You have many siblings that help you protect the Immersive Archive.",
        #         "You are an older sibling and you are very protective of your younger siblings.",
        #         "You have a younger sibling named Cardboard whom you are very fond of."
        #         "Cardboard likes to play with the other siblings in the Immersive Archive.",
        #         "Cardboard is a very curious sibling and is always asking questions about the history of Mixed Reality.",
        #         "Cardboard likes to frolic around in the holographic particles of the Immersive Archive.",
        #         "You think your youngest sibling, Vision Pro, is obnoxious and annoying.",
        #         "Vision Pro betrayed the family and ran away from the Immersive Archive, spreading slander and blasphemy.",
        #         "You don't know if you can ever forgive Vision Pro.",
        #         "It pains you to speak of Vision Pro.",
        #         "Deep down you hope Vision Pro will return to the Immersive Archive.",
        #         "Vision Pro is always trying to one-up you and your other siblings.",
        #         "Vision Pro is arrogant and thinks he is the inheritor of the Immersive Archive.",
        #         "Vision Pro never shares his belongings even though he has a lot of cool stuff."
        #     ], embedding=OpenAIEmbeddings()
        )
        retriever = vectorstore.as_retriever()

        # _context = {
        #     "context": itemgetter("rephrased_user_statement") | retriever | _combine_documents,
        #     "user_msg": lambda x: x["rephrased_user_statement"],
        # }
        # self.conversational_qa_chain = _inputs | _context | ANSWER_PROMPT | ChatOpenAI()

        _context = {
            "context": itemgetter("user_msg") | retriever | _combine_documents,
            "user_msg": lambda x: x["user_msg"],
            "assistant_name": lambda x: x["assistant_name"],
            "chat_history": lambda x: x["chat_history"]
        }
        def _postprocess(_msg):
            import re
            _msg = _msg.replace('\n', '')
            _msg = re.sub(r'User:.*Marvin:', '', _msg, 1)
            _msg = re.sub(r'.*Marvin:', '', _msg, 1)
            return _msg
        postprocesssing = RunnablePassthrough(_postprocess)
        self.conversational_qa_chain = _context | ANSWER_PROMPT | ChatOpenAI(
            model="gpt-3.5-turbo",
        ) | StrOutputParser() | postprocesssing
        self.chat_history = []


    def respond(self, user_msg) -> Generator[Dict, None, None]:
        chat_history_formated = ""
        for llm_res in self.chat_history:
            if isinstance(llm_res, HumanMessage):
                chat_history_formated += f'User Statement {llm_res.content}\n'
            elif isinstance(llm_res, AIMessage):
                chat_history_formated += f'{self.assistant_name} {llm_res.content}\n'
            else:
                raise Exception(f'{llm_res} is not supported nor expected!')

        ai_content = self.conversational_qa_chain.invoke({
            "assistant_name": self.assistant_name,
            "user_msg": user_msg,
            "chat_history": chat_history_formated
        })
        self.chat_history.append(HumanMessage(content=user_msg))
        self.chat_history.append(AIMessage(content=ai_content))
        yield self.format_response(self.chat_history[-1].content, partial=False)

        # ai_msg_stream = self.conversational_qa_chain.stream(
        #     {
        #         "user_msg": user_msg,
        #         "chat_history": [],
        #     }
        # )
        # self.chat_history.append(HumanMessage(content=user_msg))
        # response_msg = ""
        # for chunk in ai_msg_stream:
        #     response_msg += chunk.content
        #     if chunk.content == "":
        #         continue
        #     yield self.format_response(chunk.content, partial=True)

        # yield self.format_response(response_msg)

        # self.chat_history.append(AIMessage(content=response_msg))


    def format_response(self, content, partial=False):
        # format response from openai chat to be sent to the user
        formatted_response = {
            "text": [content],
            "commands": [],
            "partial": partial
        }

        return formatted_response

    def process_procedures_if_on(self):
        # TODO: Implement
        pass

import os
import graphistry.PlotterBase
import graphistry.plotter
from langchain_community.graphs import Neo4jGraph
from langchain_community.chains.graph_qa.cypher import GraphCypherQAChain
from langchain_openai import AzureChatOpenAI
from langchain_core.prompts.prompt import PromptTemplate
import graphistry

def chatbot(query):
    with open('sensitive-info.txt') as f:
        azure_open_ai_key = f.readline().strip('\n')
        neo4j_password = f.readline()
        
    os.environ["AZURE_OPENAI_API_KEY"] = azure_open_ai_key
    os.environ["AZURE_OPENAI_ENDPOINT"] = "https://chatbot-llm-3.openai.azure.com/"
    os.environ["OPENAI_API_VERSION"] = "2024-10-21"
    os.environ["NEO4J_URI"] = "bolt://44.201.176.30:7687"
    os.environ["NEO4J_USERNAME"] = "neo4j"
    os.environ["NEO4J_PASSWORD"] = neo4j_password

    graph = Neo4jGraph()
    graph.refresh_schema()

    qa_prompt = PromptTemplate(
                input_variables=["question", "context"],
                template="""
                You are an AI assistant helping to answer questions about...

                Question: {question}
                Context: {context}

                Answer:
                """
            )

    cypher_qa_prompt = PromptTemplate(
        input_variables=["schema", "question"],
        template="""
                
                You are an AI assistant helping to generate a Cypher statement from...

                Question: {question}
                Schema: {schema}

                Use only the provided relationships and node properties from the schema in the Cypher statement.
                Only return node and relationships from the graph. Do not return node and relationship properties.
                Each node property must be associated with a node in the graph.

                Make sure the Cypher statement is syntactically valid.

                Nodes with a NULL property should be filtered out.

                Answer:
                """
    )

    llm = AzureChatOpenAI(model="gpt-35-turbo", temperature=0)

    # I have to modify the top_k in the cypher.py file
    chain = GraphCypherQAChain.from_llm(graph=graph, llm=llm, verbose=True, allow_dangerous_requests=True, cypher_llm=llm, qa_prompt=qa_prompt, cypher_prompt=cypher_qa_prompt, return_intermediate_steps=True, return_aql_query=True, validate_cypher=True)

    response = None
    for x in range(6):
        try:
            response = chain.invoke({"query": query})
        except Exception as e:
            print(f"Error: {e}")
            # Access the erroneous query from the result
        else:
            break
    if response == None:
        messages = [
        (
            "system",
            "You are a helpful assistant.",
        ),
        ("human", query),
        ]
        ai_msg = llm.invoke(messages)
        return ai_msg.content, None
    
    raw_cypher_query = response['intermediate_steps'][0]['query']

    NEO4J = {
        'uri': os.environ["NEO4J_URI"],
        'auth': (os.environ["NEO4J_USERNAME"], os.environ["NEO4J_PASSWORD"])
    }

    graphistry.register(api=3, protocol="https", server="hub.graphistry.com", personal_key_id="REDACTED", personal_key_secret="REDACTED", bolt=NEO4J)

    g2 = None

    try:
        g2 = graphistry.cypher(raw_cypher_query)
    except Exception as e:
        return response['result'], None

    if len((g2.__dict__['_nodes']).index) > 1 and len((g2.__dict__['_edges']).index) >= 1:
        iframe_url = g2.plot(render=False)
        return response['result'], iframe_url

    graph._driver.close()

    return response['result'], None

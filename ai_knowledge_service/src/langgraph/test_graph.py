from graph import build_graph

if __name__ == "__main__":
    app = build_graph()

    result = app.invoke({
        "question": "Is whey protein safe for lactose intolerance?"
    })

    print("\nANSWER:\n")
    print(result["answer"])


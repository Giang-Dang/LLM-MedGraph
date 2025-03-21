from openie import StanfordOpenIE

openie_client = StanfordOpenIE()


def extract_triplets(text):
    """Extract triplets from text using Stanford OpenIE."""
    return list(openie_client.annotate(text))

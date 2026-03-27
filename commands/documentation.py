from invoke.tasks import task
from invoke import Collection


@task
def build(ctx):
    """
    Builds the project documentation using Sphinx.
    """
    with ctx.cd("docs"):
        ctx.run("make html", echo=True, pty=True)


docs_collection = Collection("docs", build)

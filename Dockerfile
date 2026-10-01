# syntax=docker/dockerfile:1
#
# IMPORTANT: set this to the EXACT same Jena/Fuseki version your local
# container runs (check `docker inspect jena_fuseki` or your compose file).
# TDB2's on-disk format is not guaranteed compatible across major Jena
# versions, so a mismatch here can produce a database Fuseki refuses to open.
ARG FUSEKI_IMAGE=stain/jena-fuseki:5.0.0
ARG DATASET_NAME=Veterinary

# ---------- Stage 1: bulk-load the TDB2 dataset ----------
FROM ${FUSEKI_IMAGE} AS loader
ARG DATASET_NAME

WORKDIR /staging
COPY data/ ./data/

# tdb2.tdbloader is the bulk loader shipped with Apache Jena — much faster
# than inserting via SPARQL UPDATE for multi-million-triple graphs.
# One --graph=<IRI> + file pair per named graph. Edit the IRIs below to
# match exactly what your local dataset uses.
RUN mkdir -p /fuseki/databases/${DATASET_NAME} && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/vetsnomed \
        data/vetsnomed.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/taxslim_full \
        data/taxslim_full.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/mondo_subset \
        data/mondo_subset.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/ncit_subset \
        data/ncit_subset.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/uberon_subset \
        data/uberon_subset.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/ncbitaxon_subset \
        data/ncbitaxon_subset.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/cell_lineage \
        data/cell_lineage.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/complete_vet_rules \
        data/complete_vet_rules.ttl && \
    tdb2.tdbloader --loc=/fuseki/databases/${DATASET_NAME} \
        --graph=http://example.org/graph/sosa_schema \
        data/sosa_schema.ttl

# ---------- Stage 2: slim runtime image ----------
# Raw RDF source files are NOT carried into this stage — only the compiled
# TDB2 database, so the final image stays lean and doesn't leak source data
# if that matters for your distribution story.
FROM ${FUSEKI_IMAGE}
ARG DATASET_NAME
ENV FUSEKI_BASE=/fuseki
ENV FUSEKI_DATASET_1=${DATASET_NAME}

COPY --from=loader /fuseki/databases/${DATASET_NAME} /fuseki/databases/${DATASET_NAME}
COPY configuration/${DATASET_NAME}.ttl /fuseki/configuration/${DATASET_NAME}.ttl

EXPOSE 3030

# Most Fuseki images auto-load every *.ttl assembler config found under
# /fuseki/configuration on startup — no extra CMD needed if that's true for
# your base image. If yours needs an explicit entrypoint arg, add it here,
# e.g.: CMD ["--config=/fuseki/configuration/Veterinary.ttl"]
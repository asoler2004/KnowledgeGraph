
docker run --init --rm -v $PWD/data:/data -p 7878:7878 oxigraph/oxigraph serve --bind 0.0.0.0:7878 --location /data

Listening for requests at http://0.0.0.0:7878

serve: Tells Oxigraph to start the web server.--bind 0.0.0.0:7878: Instructs the server to listen on all interfaces so Docker can forward the port properly.--location /data: Points the storage directory directly to the folder we mapped inside the container. [1] (https://crates.io/crates/oxigraph-cli/0.4.3)Once this runs, your server will start up normally, and you can open http://localhost:7878 to access the GUI! [1] (https://lib.rs/crates/oxigraph-cli)

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/mondo_subset_annotations.ttl http://localhost:7878/store?default

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/cl_subset_annotations.ttl http://localhost:7878/store?default

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/veterinary-ontology-rules.ttl http://localhost:7878/store?default

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/uberon_subset_annotations.ttl http://localhost:7878/store?default

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/ncit_subset_annotations.ttl http://localhost:7878/store?default

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/taxslim.owl http://localhost:7878/store?default

curl -X POST -H "Content-Type: text/turtle" --data-binary @GrafoLinfomaVet/import/vetsno_merged.ttl http://localhost:7878/store?default


para poder visualizar todo junto en la herramienta WebVowl online https://service.tib.eu/webvowl/
debemos unir todo en un solo archivo

npm install -g ttl-merge

ttl-merge -i mondo_subset_annotations.ttl cl_subset_annotations.ttl uberon_subset_annotations.ttl ncit_subset_annotations.ttl vetsno_merged.ttl taxslim_subset_annotations.ttl veterinary-ontology-rules.ttl > FullVetGraph.ttl

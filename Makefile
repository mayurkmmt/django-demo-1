.PHONY: build run stop shell manage

# If the first argument is "run"...
ifeq (manage,$(firstword $(MAKECMDGOALS)))
  # use the rest as arguments for "manage"
  RUN_ARGS := $(wordlist 2,$(words $(MAKECMDGOALS)),$(MAKECMDGOALS))
  # ...and turn them into do-nothing targets
  $(eval $(RUN_ARGS):;@:)
endif

build:
	docker build --build-arg buildmode=production --build-arg CACHEBUST=0 --tag demo1:production .

run: stop
	docker run --rm \
		-d \
		--network=host \
		-p 8080:8080 \
		-v ${PWD}/local_settings.py:/app/demo1/local_settings.py \
		-v ${PWD}/media:/app/media \
		--name demo1 \
		demo1:production

stop:
	@-docker stop demo1

shell:
	docker exec -it demo1 /bin/bash

manage:
	docker exec -w /app -it demo1 python manage.py $(RUN_ARGS)

update-lang:
	django-admin makemessages --locale=es --ignore=env/*

compile-lang:
	django-admin compilemessages

install:
	@ npm install --legacy-peer-deps

install-updates:
	@ npm install --legacy-peer-deps

list-outdated: install
	@ npm outdated --legacy-peer-deps

lint-check:
	@ npx lint

lint-check-ci:
	@ npx lint --output-file lint-check-results.json --output-file-format annotations

lint-fix:
	@ npx lint --fix

type-check:
	@ npx type-check

type-check-ci:
	@ npx type-check --output-file type-check-results.json --output-file-format annotations

security-check:
	@ # NOTE(krishan711): maybe use npm audit
	@ echo "Not Supported"

security-check-ci:
	@ echo "Not Supported"

build:
	@ NODE_ENV=production npx build-react-app-vite --config-modifier ./config.build.js

build-ssr:
	@ NODE_ENV=production npx build-react-app-ssr-vite --config-modifier ./config.build.js

build-static:
	@ NODE_ENV=production npx build-react-app-static-vite --config-modifier ./config.build.js

start:
	@ NODE_ENV=development npx build-react-app-vite --start --config-modifier ./config.build.js

start-prod:
	@ NODE_ENV=production npx build-react-app-vite --start --config-modifier ./config.build.js

test:
	@ echo "Not Supported"

clean:
	@ rm -rf ./node_modules ./package-lock.json ./build ./dist

.PHONY: *

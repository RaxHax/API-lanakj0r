# Firebase Production Setup

This guide walks through configuring Firebase so the Cloud Functions in this repository can run in a production environment with Firestore caching.

> **Prerequisites**
>
> * Firebase project with the Blaze (pay-as-you-go) plan or higher (required for outbound HTTP requests)
> * Python 3.11+
> * Firebase CLI (`npm install -g firebase-tools`)
> * gcloud CLI authenticated against the same Google Cloud project

---

## 1. Prepare Local Environment

1. **Clone the repository and install dependencies**
   ```bash
   git clone <repository-url>
   cd API-lanakj0r
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   pip install -r functions/requirements.txt
   ```
   On Windows activate the virtual environment with one of the following commands before installing requirements:
   ```cmd
   venv\Scripts\activate
   ```
   ```powershell
   .\venv\Scripts\Activate.ps1
   ```

2. **Copy the Firebase project file**
   ```bash
   cp .firebaserc.template .firebaserc
   ```
   ```cmd
   copy .firebaserc.template .firebaserc
   ```
   ```powershell
   Copy-Item .firebaserc.template .firebaserc
   ```

3. **Edit `.firebaserc`**
   Replace `your-firebase-project-id` with the actual project ID (e.g. `interest-api-prod`).

4. **Authenticate the Firebase CLI**
   ```bash
   firebase login
   firebase use your-firebase-project-id
   ```

---

## 2. Configure Firestore & Service Account

1. **Enable Firestore in native mode** from the Firebase console (Database → Create database → Native mode).

2. **Grant Firestore permissions to Cloud Functions**
   The default App Engine service account usually has the correct role. If deployments fail with permission errors, explicitly grant the following roles to the service account `your-project-id@appspot.gserviceaccount.com` via the Google Cloud Console (IAM):

   * `Cloud Datastore Owner`
   * `Service Account Token Creator`

3. **Set runtime configuration (optional)**
   If you plan to use OpenRouter AI parsing, set the key in the functions runtime:
   ```bash
   firebase functions:config:set openrouter.key="sk-or-your-key"
   ```
   In Cloud Functions for Python, runtime config entries are exposed as environment variables. You can also rely on `.env` / secret manager instead.

---

## 3. Deploy Cloud Functions

1. **Install function dependencies locally** (ensures lock files are up to date):
   ```bash
   cd functions
   pip install -r requirements.txt
   cd ..
   ```

2. **Deploy**
   ```bash
   firebase deploy --only functions
   ```

   > The deploy command automatically prepares `functions/venv` using
   > `python -m functions.devtools.ensure_venv`, so you do not need to create a
   > nested virtual environment manually. Dependencies are only reinstalled when
   > `functions/requirements.txt` changes.

3. **Verify deployment**
   ```bash
   firebase functions:list
   ```
   Copy the URLs for `get_rates` and `refresh_rates`.

---

## 4. Configure Firestore TTL (Optional)

The application enforces cache expiry in software using `Config.CACHE_DURATION_HOURS`. If you prefer using Firestore TTL policies, create one using the Google Cloud Console (Firestore → Rules → TTL). Set the policy to expire on the `last_updated` field.

---

## 5. Monitoring & Alerts

1. **Enable Cloud Logging**
   Visit Google Cloud → Logging → Logs Explorer to confirm function logs are flowing. Filter by `resource.type="cloud_function"`.

2. **Set up alerting** (optional)
   Use Cloud Monitoring to create uptime checks against the deployed endpoints and send alerts to email or Slack.

---

## 6. Continuous Integration Tips

* Add `pytest` to your CI workflow to run the unit tests introduced in this refactor.
* Use `firebase functions:config:get` and commit the output to a secure secret manager (never to Git) so deployments can be reproduced.
* Store the `serviceAccountKey.json` in a secure secret store if you use a custom service account for local development.

---

You are now ready to consume the production-ready API from your clients. For troubleshooting steps check the Firebase deployment logs (`firebase functions:log`) or Cloud Logging.

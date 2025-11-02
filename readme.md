A lightweight workflow demo that automatically builds a newsletter layout from 2–3 article links on the same website.



Features:



* Fetches and parses each article’s metadata (title, description, image).
* Automatically picks a Main Story, Other Stories, Quick Reads, and Recommended Reads.
* Outputs a responsive HTML newsletter template ready for Gmail or MailerLite.
* Works with most blog or media sites supporting Open Graph / JSON-LD.



newsletter-generator/

│

├── newsletter\_generator.py      # Main script

├── newsletter\_template.html     # HTML newsletter layout

├── urls.txt                     # Input: 2–3 article URLs (same domain)

├── requirements.txt             # Dependencies

└── README.md                    # Project documentation



Clone \& install dependencies:

git clone https://github.com/<your-username>/newsletter-generator.git

cd newsletter-generator

python -m venv venv

venv\\Scripts\\activate      # (on Mac/Linux: source venv/bin/activate)

pip install -r requirements.txt



Add url links in url.txt:

https://en.wikipedia.org/wiki/Artificial\_intelligence

https://en.wikipedia.org/wiki/Machine\_learning

https://en.wikipedia.org/wiki/Natural\_language\_processing



Run the builder:

python newsletter\_generator.py



Output: newsletter\_output.html


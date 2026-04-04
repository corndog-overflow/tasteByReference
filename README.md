taste by reference uses a Beautiful Soup based web-scraper to find all sorts of recipes. 
the raw text of the page is pulled and parsed by a local llm to JSON, JSON is validated.
the entire process is multi-threaded to allow continous work by each of the sub-processes: the scraper, llm inference and db upload.
the parsed data is uploaded to a local sqlite database, which a PyQt UI can interface with to show you recipes based on your choice of filters.

<img width="719" height="407" alt="image" src="https://github.com/user-attachments/assets/9c1f2861-9991-4cec-986f-f77752af90c1" />
<img width="448" height="66" alt="image" src="https://github.com/user-attachments/assets/8f6ceefb-22df-4094-806b-48dc4b6670c1" />


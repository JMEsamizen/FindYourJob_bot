-- Week statistics: enable linking the most in-demand skill to a W3Schools tutorial.
ALTER TABLE learning_materials ADD COLUMN IF NOT EXISTS w3_url TEXT;

UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/python/' WHERE skill = 'python' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/js/' WHERE skill = 'javascript' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/react/' WHERE skill = 'react' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/html/' WHERE skill = 'html' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/css/' WHERE skill = 'css' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/sql/' WHERE skill = 'sql' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/git/' WHERE skill = 'git' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/postgresql/' WHERE skill = 'postgresql' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/linux/' WHERE skill = 'linux' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/django/' WHERE skill = 'django' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/nodejs/' WHERE skill = 'nodejs' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/docker/' WHERE skill = 'docker' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/sql/' WHERE skill = 'rest_api' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/dsa/' WHERE skill = 'data_structures' AND w3_url IS NULL;
UPDATE learning_materials SET w3_url = 'https://www.w3schools.com/html/html_css.asp' WHERE skill = 'html_css' AND w3_url IS NULL;
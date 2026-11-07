const fs = require('fs');
const path = require('path');

const baseDir = String.raw`f:\my_exam\exam-taker\questions\nvidia-exam`;
const logFile = String.raw`f:\my_exam\exam-taker\dedup_log_node.txt`;

function log(msg) {
    console.log(msg);
    fs.appendFileSync(logFile, msg + '\n');
}

// Clear log
fs.writeFileSync(logFile, 'Starting deduplication (Node)...\n');

function getAllFiles(dirPath, arrayOfFiles) {
    const files = fs.readdirSync(dirPath);

    arrayOfFiles = arrayOfFiles || [];

    files.forEach(function(file) {
        if (fs.statSync(dirPath + "/" + file).isDirectory()) {
            arrayOfFiles = getAllFiles(dirPath + "/" + file, arrayOfFiles);
        } else {
            if (file.endsWith('.json')) {
                arrayOfFiles.push(path.join(dirPath, file));
            }
        }
    });

    return arrayOfFiles;
}

try {
    log(`Scanning directories in ${baseDir}...`);
    
    // We need to process per folder to match the python logic "unique within each folder"
    // So let's iterate folders in baseDir
    const items = fs.readdirSync(baseDir);
    
    items.forEach(item => {
        const itemPath = path.join(baseDir, item);
        if (fs.statSync(itemPath).isDirectory()) {
            log(`Checking folder: ${itemPath}`);
            
            const jsonFiles = fs.readdirSync(itemPath).filter(f => f.endsWith('.json'));
            
            const idMap = {}; // id -> [{file, index}]
            const fileData = {};
            const dirtyFiles = new Set();
            
            // Load phase
            jsonFiles.forEach(fname => {
                const fpath = path.join(itemPath, fname);
                try {
                    const content = JSON.parse(fs.readFileSync(fpath, 'utf8'));
                    if (Array.isArray(content)) {
                        fileData[fname] = content;
                        content.forEach((q, idx) => {
                            if (q && q.id) {
                                if (!idMap[q.id]) idMap[q.id] = [];
                                idMap[q.id].push({fname, idx});
                            }
                        });
                    }
                } catch (e) {
                    log(`Error reading ${fname}: ${e.message}`);
                }
            });
            
            // Deduplication phase
            for (const qid in idMap) {
                const locations = idMap[qid];
                if (locations.length > 1) {
                    log(`  Duplicate ID '${qid}' found ${locations.length} times.`);
                    
                    // Sort by filename then index to be deterministic
                    locations.sort((a, b) => {
                        if (a.fname < b.fname) return -1;
                        if (a.fname > b.fname) return 1;
                        return a.idx - b.idx;
                    });
                    
                    // Rename duplicates (skip the first one)
                    for (let i = 1; i < locations.length; i++) {
                        const loc = locations[i];
                        const newId = `${qid}_v${i}`;
                        log(`    Renaming in ${loc.fname}: ${qid} -> ${newId}`);
                        fileData[loc.fname][loc.idx].id = newId;
                        dirtyFiles.add(loc.fname);
                    }
                }
            }
            
            // Save phase
            dirtyFiles.forEach(fname => {
                const fpath = path.join(itemPath, fname);
                try {
                    fs.writeFileSync(fpath, JSON.stringify(fileData[fname], null, 4), 'utf8');
                    log(`  Saved updates to ${fname}`);
                } catch (e) {
                    log(`Error writing ${fname}: ${e.message}`);
                }
            });
        }
    });
    
    log("Done.");
} catch (e) {
    log(`Fatal error: ${e.message}`);
}

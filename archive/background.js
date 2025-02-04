const API_ENDPOINT = 'http://localhost:8000/api/extension-data';

async function sendDataToBackend(data) {
    try {
        console.log('Attempting to send data:', data);
        
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify(data)
        });

        // For debugging
        console.log('Response status:', response.status);
        const responseText = await response.text();
        console.log('Response body:', responseText);

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}, body: ${responseText}`);
        }

        const result = JSON.parse(responseText);
        console.log('Success:', result);
        return result;
    } catch (error) {
        console.error('Error sending data:', error);
        throw error;
    }
}

// Create new tab and collect data
chrome.tabs.create(
    { url: 'https://www.jackandamydev.com' },
    (tab) => {
        // Wait for the tab to complete loading
        chrome.tabs.onUpdated.addListener(function listener(tabId, info) {
            if (tabId === tab.id && info.status === 'complete') {
                chrome.tabs.onUpdated.removeListener(listener);
                
                // Execute script in the tab
                chrome.tabs.executeScript(tab.id, {
                    code: `
                    ({
                        url: window.location.href,
                        title: document.title,
                        timestamp: new Date().toISOString(),
                        userId: '${chrome.runtime.id}'
                    })
                    `
                }, async (results) => {
                    if (chrome.runtime.lastError) {
                        console.error('Script execution error:', chrome.runtime.lastError);
                        return;
                    }

                    if (results && results[0]) {
                        try {
                            await sendDataToBackend(results[0]);
                        } catch (error) {
                            console.error('Error processing data:', error);
                        }
                    }
                });
            }
        });
    }
);


// console.log('chrome.tabs.create')
// chrome.tabs.create(
//     { url: 'https://jackandamydev.com'},
//     (tab) => {
//         console.log('chrome.tabs.executeScript')
//         chrome.tabs.executeScript(tab.id, {
//             code: 'alert(location.href)',
//         })
//     },
// )

// setTimeout(() => {
//     const matchPattern = 'https://jackandamydev.com/*'
//     console.log('chrome.tabs.query by url')
//     chrome.tabs.query({url : matchPattern}, (tabs) => {
//         console.log(matchPattern, JSON.stringify(tabs, undefined, 2))
//     })
// }, 3000)

// setTimeout(() => {
//     chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
//         console.count('chrome.tabs.onUpdated')
//         console.log(tabId, JSON.stringify(changeInfo, undefined, 2))
//     })
// }, 4000);
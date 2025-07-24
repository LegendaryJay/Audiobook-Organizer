// API endpoint to test series lookup
export async function POST({ request }) {
  try {
    const { title, author } = await request.json();
    
    if (!title) {
      return new Response(JSON.stringify({ 
        success: false, 
        error: 'Title is required' 
      }), { 
        status: 400, 
        headers: { 'Content-Type': 'application/json' } 
      });
    }

    // Call the Python backend series test endpoint
    const response = await fetch('http://localhost:4000/api/test-series', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ title, author })
    });

    if (!response.ok) {
      throw new Error(`Backend returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
    
    return new Response(JSON.stringify({ 
      success: true, 
      data: data
    }), { 
      status: 200, 
      headers: { 'Content-Type': 'application/json' } 
    });

  } catch (error) {
    console.error('Series lookup error:', error);
    
    return new Response(JSON.stringify({ 
      success: false, 
      error: error.message || 'Failed to lookup series information'
    }), { 
      status: 500, 
      headers: { 'Content-Type': 'application/json' } 
    });
  }
}

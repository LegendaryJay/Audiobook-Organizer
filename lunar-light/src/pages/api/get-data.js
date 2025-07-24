// API endpoint to get current audiobook data
export async function GET({ request }) {
  try {
    console.log('Get data API called');
    
    // Call the Python backend to get current audiobook data
    const response = await fetch('/api/audiobooks', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      }
    });
    
    if (!response.ok) {
      console.log('Backend not available, returning empty data');
      return new Response(JSON.stringify({ 
        success: true, 
        data: { total: 0, items: [] }
      }), { 
        status: 200, 
        headers: { 'Content-Type': 'application/json' } 
      });
    }
    
    const data = await response.json();
    console.log('Backend data response:', data);
    
    return new Response(JSON.stringify({ 
      success: true, 
      data: data
    }), { 
      status: 200, 
      headers: { 'Content-Type': 'application/json' } 
    });
    
  } catch (error) {
    console.error('Get data error:', error);
    
    // Return empty data if backend is not available
    return new Response(JSON.stringify({ 
      success: true, 
      data: { total: 0, items: [] }
    }), { 
      status: 200, 
      headers: { 'Content-Type': 'application/json' } 
    });
  }
}

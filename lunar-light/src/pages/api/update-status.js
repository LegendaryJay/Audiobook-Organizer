// API endpoint to update status of audiobook items
export async function POST({ request }) {
  try {
    const { uuid, status } = await request.json();
    
    if (!uuid || !status) {
      return new Response(JSON.stringify({ 
        success: false, 
        error: 'Invalid input: uuid and status are required' 
      }), { 
        status: 400, 
        headers: { 'Content-Type': 'application/json' } 
      });
    }

    console.log('Update status request:', { uuid, status });

    // Call the Python backend to update status using UUID
    const response = await fetch(`http://localhost:4000/api/audiobooks/${uuid}/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status })
    });

    console.log('Backend response status:', response.status);
    console.log('Backend response headers:', response.headers);

    if (!response.ok) {
      const responseText = await response.text();
      console.log('Backend error response:', responseText);
      let errorData = {};
      try {
        errorData = JSON.parse(responseText);
      } catch (e) {
        console.log('Failed to parse error response as JSON');
      }
      throw new Error(errorData.error || `Backend returned ${response.status}: ${response.statusText}`);
    }

    const responseText = await response.text();
    console.log('Backend success response:', responseText);
    
    let data = {};
    try {
      data = JSON.parse(responseText);
    } catch (e) {
      console.log('Failed to parse success response as JSON');
      throw new Error('Invalid JSON response from backend');
    }
    console.log('Status update response:', data);

    return new Response(JSON.stringify({ 
      success: true,
      message: 'Status updated successfully'
    }), { 
      status: 200, 
      headers: { 'Content-Type': 'application/json' } 
    });

  } catch (error) {
    console.error('Update status error:', error);
    
    return new Response(JSON.stringify({ 
      success: false, 
      error: error.message || 'Failed to update status'
    }), { 
      status: 500, 
      headers: { 'Content-Type': 'application/json' } 
    });
  }
}

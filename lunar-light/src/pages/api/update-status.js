// API endpoint to update status of audiobook items
export async function POST({ request }) {
  try {
    const { index, status } = await request.json();
    
    if (typeof index !== 'number' || !status) {
      return new Response(JSON.stringify({ 
        success: false, 
        error: 'Invalid input: index and status are required' 
      }), { 
        status: 400, 
        headers: { 'Content-Type': 'application/json' } 
      });
    }

    // Call the Python backend to update status
    const response = await fetch(`http://localhost:4000/api/audiobooks/${index}/status`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ status })
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.error || `Backend returned ${response.status}: ${response.statusText}`);
    }

    const data = await response.json();
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

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import ModelModal from '@/components/ModelModal';
import { apiClient } from '@/lib/api';

jest.mock('@/lib/api', () => ({
  apiClient: {
    get: jest.fn(() => Promise.resolve(['Coding', 'General'])),
    post: jest.fn(),
    put: jest.fn()
  }
}));

describe('ModelModal', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders modal fields and handles close', async () => {
    const handleClose = jest.fn();
    const handleSuccess = jest.fn();

    render(
      <ModelModal 
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    expect(screen.getByText('Add a model')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('e.g. Llama-3-8B')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Cancel'));
    expect(handleClose).toHaveBeenCalled();
  });

  it('submits POST request with form data on create submit', async () => {
    (apiClient.post as jest.Mock).mockResolvedValue({ id: '1' });
    const handleClose = jest.fn();
    const handleSuccess = jest.fn();

    render(
      <ModelModal 
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Coding')).toBeInTheDocument();
    });

    // Populate inputs
    fireEvent.change(screen.getByPlaceholderText('e.g. Llama-3-8B'), { target: { name: 'name', value: 'Test Model' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. QuantFactory/Meta-Llama-3-8B-Instruct-GGUF'), { target: { name: 'hf_repo_id', value: 'repo/id' } });
    fireEvent.change(screen.getByPlaceholderText('e.g. Meta-Llama-3-8B-Instruct.Q4_K_M.gguf'), { target: { name: 'gguf_filename', value: 'model.gguf' } });
    
    // Toggle task
    fireEvent.click(screen.getByLabelText('Coding'));

    // Add arguments
    fireEvent.click(screen.getByText('+ Add Argument'));
    
    const keyInputs = screen.getAllByPlaceholderText('Key (e.g. -ngl)');
    const valInputs = screen.getAllByPlaceholderText('Value (e.g. 99)');
    
    fireEvent.change(keyInputs[0], { target: { value: '-ngl' } });
    fireEvent.change(valInputs[0], { target: { value: '99' } });

    // Submit form
    fireEvent.click(screen.getByRole('button', { name: 'Add Model' }));

    await waitFor(() => {
      expect(apiClient.post).toHaveBeenCalledWith('/models', expect.objectContaining({
        name: 'Test Model',
        hf_repo_id: 'repo/id',
        gguf_filename: 'model.gguf',
        recommended_tasks: ['Coding'],
        llamacpp_args: {
          '-ngl': 99
        }
      }));
      expect(handleSuccess).toHaveBeenCalled();
    });
  });

  it('submits PUT request with edited data on edit submit', async () => {
    (apiClient.put as jest.Mock).mockResolvedValue({ id: '1' });
    const handleClose = jest.fn();
    const handleSuccess = jest.fn();
    const initialData = {
      id: '1',
      name: 'Old Model',
      hf_repo_id: 'old/repo',
      gguf_filename: 'old.gguf',
      ram_required_mb: 8192,
      context_size: 4096,
      llamacpp_version_hash: 'ff52ee9',
      recommended_tasks: ['General'],
      llamacpp_args: {
        '-ngl': 'true',
        '-other': 'false'
      }
    };

    render(
      <ModelModal 
        initialData={initialData}
        onClose={handleClose}
        onSuccess={handleSuccess}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('General')).toBeInTheDocument();
    });

    // Verify fields populated
    expect(screen.getByDisplayValue('Old Model')).toBeInTheDocument();

    // Toggle tasks
    fireEvent.click(screen.getByLabelText('Coding')); // Add Coding
    fireEvent.click(screen.getByLabelText('General')); // Remove General

    // Add and remove arguments
    fireEvent.click(screen.getByText('+ Add Argument'));
    
    // There are three rows now: ngl, other, new
    const removeBtns = screen.getAllByText('×');
    fireEvent.click(removeBtns[2]); // Remove the second arg (other), index 0 is close, index 1 is ngl, index 2 is other

    // Submit
    fireEvent.click(screen.getByRole('button', { name: 'Update Model' }));

    await waitFor(() => {
      expect(apiClient.put).toHaveBeenCalledWith('/models/1', expect.objectContaining({
        name: 'Old Model',
        recommended_tasks: ['Coding'],
        llamacpp_args: {
          '-ngl': true // converted to boolean true
        }
      }));
      expect(handleSuccess).toHaveBeenCalled();
    });
  });
});

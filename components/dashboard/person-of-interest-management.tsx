"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2, UserPlus, X, Save, Upload, Download, Camera, RefreshCw, Cloud, Database } from "lucide-react";
import { apiClient } from "@/lib/api-client";

interface PersonOfInterest {
  id?: number;
  name: string;
  phone_number: string;
  photograph_base64: string;
  details: Record<string, any>;
  created_at?: string;
  updated_at?: string;
}

interface PersonOfInterestCardProps {
  person: PersonOfInterest;
  personIndex: number;
  onUpdate: (person: PersonOfInterest) => void;
  onDelete: () => void;
}

function PersonOfInterestCard({ person, personIndex, onUpdate, onDelete }: PersonOfInterestCardProps) {
  const [editedPerson, setEditedPerson] = useState<PersonOfInterest>(person);
  const [additionalFields, setAdditionalFields] = useState<Array<{ key: string; value: string }>>(
    Object.entries(person.details || {}).map(([key, value]) => ({ key, value: String(value) }))
  );
  const [isEditing, setIsEditing] = useState(false);

  const compressImage = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const reader = new FileReader();
      reader.onload = (e) => {
        const img = new Image();
        img.onload = () => {
          // Create canvas for compression
          const canvas = document.createElement('canvas');
          const ctx = canvas.getContext('2d');
          
          if (!ctx) {
            reject(new Error('Failed to get canvas context'));
            return;
          }

          // Calculate new dimensions (max 800x800, maintain aspect ratio)
          let width = img.width;
          let height = img.height;
          const maxDimension = 800;

          if (width > height && width > maxDimension) {
            height = (height * maxDimension) / width;
            width = maxDimension;
          } else if (height > maxDimension) {
            width = (width * maxDimension) / height;
            height = maxDimension;
          }

          canvas.width = width;
          canvas.height = height;

          // Draw and compress
          ctx.drawImage(img, 0, 0, width, height);
          
          // Convert to base64 with quality compression (0.7 = 70% quality)
          const compressedBase64 = canvas.toDataURL('image/jpeg', 0.7);
          resolve(compressedBase64);
        };
        img.onerror = () => reject(new Error('Failed to load image'));
        img.src = e.target?.result as string;
      };
      reader.onerror = () => reject(new Error('Failed to read file'));
      reader.readAsDataURL(file);
    });
  };

  const handlePhotoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      try {
        // Compress the image before saving
        const compressedBase64 = await compressImage(file);
        setEditedPerson({ ...editedPerson, photograph_base64: compressedBase64 });
        setIsEditing(true);
      } catch (error) {
        console.error('Error compressing image:', error);
        alert('Failed to process image. Please try a different image.');
      }
    }
  };

  const addField = () => {
    setAdditionalFields([...additionalFields, { key: "", value: "" }]);
    setIsEditing(true);
  };

  const updateField = (index: number, key: string, value: string) => {
    const updated = [...additionalFields];
    updated[index] = { key, value };
    setAdditionalFields(updated);
    setIsEditing(true);
  };

  const removeField = (index: number) => {
    setAdditionalFields(additionalFields.filter((_, i) => i !== index));
    setIsEditing(true);
  };

  const saveChanges = () => {
    // Convert additional fields to details object
    const details: Record<string, any> = {};
    additionalFields.forEach(field => {
      if (field.key.trim()) {
        details[field.key.trim()] = field.value;
      }
    });

    const updatedPerson = {
      ...editedPerson,
      details
    };

    onUpdate(updatedPerson);
    setIsEditing(false);
  };

  const cancelChanges = () => {
    setEditedPerson(person);
    setAdditionalFields(
      Object.entries(person.details || {}).map(([key, value]) => ({ key, value: String(value) }))
    );
    setIsEditing(false);
  };

  return (
    <Card className="relative">
      <CardHeader>
        <div className="flex items-center justify-between">
          <div className="flex-1">
            <CardTitle className="flex items-center gap-2">
              <span className="text-sm font-medium text-muted-foreground">Person #{personIndex + 1}</span>
              {editedPerson.name && (
                <span className="text-base font-bold">- {editedPerson.name}</span>
              )}
            </CardTitle>
            <CardDescription>
              Phone: {editedPerson.phone_number || "Not set"} • {additionalFields.length} additional field(s)
            </CardDescription>
          </div>
          <Button
            variant="destructive"
            size="sm"
            onClick={onDelete}
            className="shrink-0"
          >
            <Trash2 className="h-4 w-4 mr-1" />
            Delete
          </Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Mandatory Fields */}
        <div className="space-y-3 border-b pb-4">
          <h3 className="text-sm font-semibold text-red-600">Mandatory Fields *</h3>
          
          {/* Photo Upload */}
          <div>
            <Label htmlFor={`photo-${personIndex}`}>Photograph *</Label>
            <p className="text-xs text-muted-foreground mb-1">
              Images will be automatically compressed to reduce size
            </p>
            <div className="flex items-center gap-2 mt-1">
              {editedPerson.photograph_base64 && (
                <img 
                  src={editedPerson.photograph_base64} 
                  alt="Person"
                  className="w-20 h-20 object-cover rounded border"
                />
              )}
              <div className="flex-1">
                <input
                  type="file"
                  id={`photo-${personIndex}`}
                  className="hidden"
                  accept="image/*"
                  onChange={handlePhotoUpload}
                />
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => document.getElementById(`photo-${personIndex}`)?.click()}
                >
                  <Camera className="h-4 w-4 mr-1" />
                  {editedPerson.photograph_base64 ? "Change Photo" : "Upload Photo"}
                </Button>
              </div>
            </div>
          </div>

          {/* Name */}
          <div>
            <Label htmlFor={`name-${personIndex}`}>Name *</Label>
            <Input
              id={`name-${personIndex}`}
              placeholder="Full name"
              value={editedPerson.name}
              onChange={(e) => {
                setEditedPerson({ ...editedPerson, name: e.target.value });
                setIsEditing(true);
              }}
              className="font-medium"
            />
          </div>

          {/* Phone Number */}
          <div>
            <Label htmlFor={`phone-${personIndex}`}>Phone Number *</Label>
            <Input
              id={`phone-${personIndex}`}
              placeholder="+1234567890"
              value={editedPerson.phone_number}
              onChange={(e) => {
                setEditedPerson({ ...editedPerson, phone_number: e.target.value });
                setIsEditing(true);
              }}
              className="font-medium"
            />
          </div>
        </div>

        {/* Additional Fields */}
        <div className="space-y-3">
          <h3 className="text-sm font-semibold">Additional Fields (Optional)</h3>
          
          {additionalFields.map((field, index) => (
            <div key={index} className="flex items-center gap-2">
              <div className="grid grid-cols-2 gap-2 flex-1">
                <Input
                  placeholder="Field name (e.g., Address)"
                  value={field.key}
                  onChange={(e) => updateField(index, e.target.value, field.value)}
                />
                <Input
                  placeholder="Value"
                  value={field.value}
                  onChange={(e) => updateField(index, field.key, e.target.value)}
                />
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeField(index)}
                className="shrink-0"
              >
                <X className="h-4 w-4 text-red-500" />
              </Button>
            </div>
          ))}

          <Button
            variant="outline"
            size="sm"
            onClick={addField}
          >
            <Plus className="h-4 w-4 mr-1" />
            Add Field
          </Button>
        </div>

        {/* Action Buttons */}
        {isEditing && (
          <div className="flex gap-2 pt-4 border-t">
            <Button
              variant="default"
              size="sm"
              onClick={saveChanges}
            >
              <Save className="h-4 w-4 mr-1" />
              Save Changes
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={cancelChanges}
            >
              Cancel
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

interface PersonOfInterestManagementProps {
  suspects?: any[];
  onSuspectsChange?: (suspects: any[]) => void;
}

export function PersonOfInterestManagement({ suspects = [], onSuspectsChange }: PersonOfInterestManagementProps) {
  const [persons, setPersons] = useState<PersonOfInterest[]>([]);
  const [loading, setLoading] = useState(false);
  const [syncStatus, setSyncStatus] = useState<'synced' | 'unsynced' | 'error'>('unsynced');
  const [lastSync, setLastSync] = useState<Date | null>(null);

  // Load POIs from backend on mount
  React.useEffect(() => {
    loadFromBackend();
  }, []);

  // Sync with parent component if controlled
  React.useEffect(() => {
    if (suspects && suspects.length > 0) {
      // Convert suspects to PersonOfInterest format if needed
      const converted = suspects.map(s => ({
        id: s.id,
        name: s.name || "",
        phone_number: s.phone_number || "",
        photograph_base64: s.photograph_base64 || "",
        details: s.details || {},
        created_at: s.created_at,
        updated_at: s.updated_at
      }));
      setPersons(converted);
    }
  }, [suspects]);

  // Backend sync functions
  const loadFromBackend = async () => {
    setLoading(true);
    try {
      const backendPOIs = await apiClient.poi.getAll();
      console.log('Loaded POIs from backend:', backendPOIs.length);
      
      // Convert backend POIs to local format
      const converted = backendPOIs.map(poi => ({
        id: poi.id,
        name: poi.name,
        phone_number: poi.phone_number,
        photograph_base64: poi.photograph_base64,
        details: poi.details || {},
        created_at: poi.created_at,
        updated_at: poi.updated_at
      }));
      
      setPersons(converted);
      setSyncStatus('synced');
      setLastSync(new Date());
      
      if (onSuspectsChange) {
        onSuspectsChange(converted);
      }
    } catch (error) {
      console.error('Failed to load POIs from backend:', error);
      setSyncStatus('error');
      alert('Failed to load POIs from backend. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const saveToBackend = async () => {
    setLoading(true);
    try {
      let successCount = 0;
      let errorCount = 0;

      for (const person of persons) {
        try {
          if (person.id) {
            // Update existing POI
            await apiClient.poi.update(person.id, {
              name: person.name,
              phone_number: person.phone_number,
              photograph_base64: person.photograph_base64,
              details: person.details
            });
          } else {
            // Create new POI
            const created = await apiClient.poi.create({
              name: person.name,
              phone_number: person.phone_number,
              photograph_base64: person.photograph_base64,
              details: person.details
            });
            // Update local person with backend ID
            person.id = created.id;
          }
          successCount++;
        } catch (error) {
          console.error(`Failed to sync POI ${person.name}:`, error);
          errorCount++;
        }
      }

      if (errorCount === 0) {
        setSyncStatus('synced');
        setLastSync(new Date());
        alert(`✅ Successfully synced ${successCount} POI(s) to backend`);
      } else {
        setSyncStatus('error');
        alert(`⚠️ Synced ${successCount} POI(s), but ${errorCount} failed. Check console for details.`);
      }
    } catch (error) {
      console.error('Failed to save POIs to backend:', error);
      setSyncStatus('error');
      alert('Failed to save POIs to backend. Check console for details.');
    } finally {
      setLoading(false);
    }
  };

  const importToBackend = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        
        // Support multiple file formats
        let importedPersons: PersonOfInterest[] = [];
        
        if (data.persons && Array.isArray(data.persons)) {
          importedPersons = data.persons;
        } else if (data.suspects && Array.isArray(data.suspects)) {
          importedPersons = data.suspects;
        } else if (Array.isArray(data)) {
          importedPersons = data;
        } else {
          throw new Error('Invalid file format. Expected JSON with "persons" or "suspects" array.');
        }
        
        // Validate required fields
        const validated = importedPersons.filter((p, idx) => {
          if (!p.name || !p.phone_number || !p.photograph_base64) {
            console.warn(`Skipping invalid POI at index ${idx}`);
            return false;
          }
          return true;
        });
        
        if (validated.length === 0) {
          throw new Error('No valid persons found. Each person must have name, phone_number, and photograph_base64.');
        }
        
        // Import to backend via API
        setLoading(true);
        try {
          const result = await apiClient.poi.importBulk(validated);
          console.log('Import result:', result);
          
          // Reload from backend to get updated list with IDs
          await loadFromBackend();
          
          alert(`✅ Successfully imported ${result.created} POI(s) to backend`);
        } catch (error) {
          console.error('Failed to import to backend:', error);
          alert('Failed to import to backend. Check console for details.');
        } finally {
          setLoading(false);
        }
        
      } catch (error) {
        console.error('Failed to import:', error);
        alert(`Failed to import file:\n${error instanceof Error ? error.message : 'Unknown error'}`);
      }
    };
    reader.readAsText(file);
    event.target.value = '';
  };

  const updateParent = (updated: PersonOfInterest[]) => {
    setPersons(updated);
    setSyncStatus('unsynced'); // Mark as unsynced when local changes are made
    if (onSuspectsChange) {
      onSuspectsChange(updated);
    }
  };

  const addPerson = () => {
    const newPerson: PersonOfInterest = {
      name: "",
      phone_number: "",
      photograph_base64: "",
      details: {}
    };
    updateParent([...persons, newPerson]);
  };

  const updatePerson = async (index: number, updatedPerson: PersonOfInterest) => {
    const updated = [...persons];
    updated[index] = updatedPerson;
    updateParent(updated);
    
    // Auto-sync to backend if person has an ID
    if (updatedPerson.id) {
      try {
        await apiClient.poi.update(updatedPerson.id, {
          name: updatedPerson.name,
          phone_number: updatedPerson.phone_number,
          photograph_base64: updatedPerson.photograph_base64,
          details: updatedPerson.details
        });
        console.log(`Auto-synced POI ${updatedPerson.id} to backend`);
      } catch (error) {
        console.error('Failed to auto-sync POI:', error);
        setSyncStatus('error');
      }
    }
  };

  const deletePerson = async (index: number) => {
    const person = persons[index];
    
    // Delete from backend if it has an ID
    if (person.id) {
      const confirmDelete = window.confirm(
        `Delete "${person.name}" from backend?\n\nThis will remove the POI and all associated face encodings.`
      );
      
      if (!confirmDelete) return;
      
      try {
        await apiClient.poi.delete(person.id);
        console.log(`Deleted POI ${person.id} from backend`);
      } catch (error) {
        console.error('Failed to delete from backend:', error);
        alert('Failed to delete from backend. The POI will be removed locally.');
      }
    }
    
    updateParent(persons.filter((_, i) => i !== index));
  };

  const exportData = () => {
    const dataStr = JSON.stringify({ persons }, null, 2);
    const dataBlob = new Blob([dataStr], { type: 'application/json' });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `persons-of-interest-${Date.now()}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const importData = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = JSON.parse(e.target?.result as string);
        
        // Support multiple file formats
        let importedPersons: PersonOfInterest[] = [];
        
        if (data.persons && Array.isArray(data.persons)) {
          importedPersons = data.persons;
        } else if (data.suspects && Array.isArray(data.suspects)) {
          importedPersons = data.suspects;
        } else if (Array.isArray(data)) {
          importedPersons = data;
        } else {
          throw new Error('Invalid file format. Expected JSON with "persons" or "suspects" array.');
        }
        
        // Validate required fields
        const validated = importedPersons.filter((p, idx) => {
          if (!p.name || !p.phone_number || !p.photograph_base64) {
            console.warn(`Skipping invalid POI at index ${idx}:`, {
              hasName: !!p.name,
              hasPhone: !!p.phone_number,
              hasPhoto: !!p.photograph_base64
            });
            return false;
          }
          return true;
        });
        
        if (validated.length === 0) {
          throw new Error('No valid persons found. Each person must have name, phone_number, and photograph_base64.');
        }
        
        // Ask user: replace or merge?
        const shouldReplace = window.confirm(
          `Found ${validated.length} valid person(s) in file.\n\n` +
          `Click OK to REPLACE existing persons.\n` +
          `Click Cancel to MERGE with existing persons.`
        );
        
        if (shouldReplace) {
          updateParent(validated);
          alert(`✅ Replaced with ${validated.length} person(s)`);
        } else {
          updateParent([...persons, ...validated]);
          alert(`✅ Added ${validated.length} person(s) to existing ${persons.length}`);
        }
        
        const skipped = importedPersons.length - validated.length;
        if (skipped > 0) {
          console.warn(`Skipped ${skipped} invalid entries`);
        }
        
      } catch (error) {
        console.error('Failed to import:', error);
        alert(`Failed to import file:\n${error instanceof Error ? error.message : 'Unknown error'}\n\nPlease ensure it's a valid JSON file with required fields.`);
      }
    };
    reader.onerror = () => {
      alert('Failed to read file. Please try again.');
    };
    reader.readAsText(file);
    
    // Reset input to allow re-importing same file
    event.target.value = '';
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Persons of Interest</h2>
          <p className="text-muted-foreground">
            Manage persons with mandatory name, phone, and photo fields
          </p>
          {lastSync && (
            <p className="text-xs text-muted-foreground mt-1">
              Last synced: {lastSync.toLocaleString()}
            </p>
          )}
        </div>
        <div className="flex gap-2">
          {/* Backend Sync Controls */}
          <Button
            variant="outline"
            onClick={loadFromBackend}
            disabled={loading}
            title="Load POIs from backend"
          >
            {loading ? (
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Cloud className="h-4 w-4 mr-1" />
            )}
            Load
          </Button>
          <Button
            variant={syncStatus === 'unsynced' ? 'default' : 'outline'}
            onClick={saveToBackend}
            disabled={loading || persons.length === 0}
            title="Save all POIs to backend"
          >
            {loading ? (
              <RefreshCw className="h-4 w-4 mr-1 animate-spin" />
            ) : (
              <Database className="h-4 w-4 mr-1" />
            )}
            {syncStatus === 'unsynced' ? 'Sync to Backend' : 'Save'}
          </Button>
          
          {/* Import/Export Controls */}
          <input
            type="file"
            id="import-poi"
            className="hidden"
            accept=".json"
            onChange={importData}
          />
          <input
            type="file"
            id="import-poi-backend"
            className="hidden"
            accept=".json"
            onChange={importToBackend}
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('import-poi')?.click()}
            title="Import to local state only"
          >
            <Upload className="h-4 w-4 mr-1" />
            Import Local
          </Button>
          <Button
            variant="outline"
            onClick={() => document.getElementById('import-poi-backend')?.click()}
            title="Import and sync to backend immediately"
          >
            <Upload className="h-4 w-4 mr-1" />
            <Database className="h-3 w-3" />
            Import to Backend
          </Button>
          <Button
            variant="outline"
            onClick={exportData}
            disabled={persons.length === 0}
          >
            <Download className="h-4 w-4 mr-1" />
            Export
          </Button>
          <Button onClick={addPerson}>
            <UserPlus className="h-4 w-4 mr-2" />
            Add Person
          </Button>
        </div>
      </div>

      {/* Sync Status Indicator */}
      {syncStatus !== 'synced' && persons.length > 0 && (
        <div className={`p-3 rounded-lg border ${
          syncStatus === 'error' 
            ? 'bg-red-50 border-red-200 text-red-700' 
            : 'bg-yellow-50 border-yellow-200 text-yellow-700'
        }`}>
          <div className="flex items-center gap-2">
            {syncStatus === 'error' ? (
              <>
                <X className="h-4 w-4" />
                <span className="text-sm font-medium">Sync error - check console for details</span>
              </>
            ) : (
              <>
                <RefreshCw className="h-4 w-4" />
                <span className="text-sm font-medium">Local changes not synced to backend</span>
                <Button
                  size="sm"
                  variant="outline"
                  onClick={saveToBackend}
                  disabled={loading}
                  className="ml-auto"
                >
                  Sync Now
                </Button>
              </>
            )}
          </div>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>Total Persons</CardDescription>
            <CardTitle className="text-3xl">{persons.length}</CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>With Photos</CardDescription>
            <CardTitle className="text-3xl">
              {persons.filter(p => p.photograph_base64).length}
            </CardTitle>
          </CardHeader>
        </Card>
        <Card>
          <CardHeader className="pb-3">
            <CardDescription>With Phone Numbers</CardDescription>
            <CardTitle className="text-3xl">
              {persons.filter(p => p.phone_number).length}
            </CardTitle>
          </CardHeader>
        </Card>
      </div>

      {/* Persons List */}
      {persons.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <UserPlus className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
            <h3 className="text-lg font-medium mb-2">No persons added yet</h3>
            <p className="text-muted-foreground mb-4">
              Start by adding a person of interest with name, phone, and photo
            </p>
            <Button onClick={addPerson}>
              <UserPlus className="h-4 w-4 mr-2" />
              Add Your First Person
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-4">
          {persons.map((person, index) => (
            <PersonOfInterestCard
              key={index}
              person={person}
              personIndex={index}
              onUpdate={(updated) => updatePerson(index, updated)}
              onDelete={() => deletePerson(index)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

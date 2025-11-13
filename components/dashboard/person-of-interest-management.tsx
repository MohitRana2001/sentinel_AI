"use client";

import React, { useState, useEffect } from "react";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Plus, Trash2, UserPlus, X, Save, Upload, Download, Camera } from "lucide-react";

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

  const handlePhotoUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64 = reader.result as string;
        setEditedPerson({ ...editedPerson, photograph_base64: base64 });
        setIsEditing(true);
      };
      reader.readAsDataURL(file);
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

  // Sync with parent component if controlled
  React.useEffect(() => {
    if (suspects && suspects.length > 0) {
      // Convert suspects to PersonOfInterest format if needed
      const converted = suspects.map(s => ({
        name: s.name || "",
        phone_number: s.phone_number || "",
        photograph_base64: s.photograph_base64 || "",
        details: s.details || {}
      }));
      setPersons(converted);
    }
  }, [suspects]);

  const updateParent = (updated: PersonOfInterest[]) => {
    setPersons(updated);
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

  const updatePerson = (index: number, updatedPerson: PersonOfInterest) => {
    const updated = [...persons];
    updated[index] = updatedPerson;
    updateParent(updated);
  };

  const deletePerson = (index: number) => {
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
        if (data.persons && Array.isArray(data.persons)) {
          setPersons(data.persons);
        }
      } catch (error) {
        console.error('Failed to import:', error);
        alert('Failed to import file. Please ensure it\'s a valid JSON file.');
      }
    };
    reader.readAsText(file);
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
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            id="import-poi"
            className="hidden"
            accept=".json"
            onChange={importData}
          />
          <Button
            variant="outline"
            onClick={() => document.getElementById('import-poi')?.click()}
          >
            <Upload className="h-4 w-4 mr-1" />
            Import
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
